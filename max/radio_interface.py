"""
Simple interface for reading signal data from MeshCore radio using trace commands.

Used by Signal Mapper WebSocket consumer for on-demand signal readings.
"""

import asyncio
import logging
import time
from meshcore import MeshCore, SerialConnection, EventType
from django.conf import settings

logger = logging.getLogger(__name__)


class RadioInterface:
    """
    Interface to read signal data from MeshCore radio using trace commands.
    """

    def __init__(self, port=None):
        """
        Initialize radio interface.

        Args:
            port: Serial port path (default from settings)
        """
        self.port = port or settings.MESHCORE_SERIAL_PORT
        self.mc = None
        self.serial_cx = None
        logger.info(f"Radio interface initialized for {self.port}")

    async def connect(self):
        """Open async serial connection to radio."""
        try:
            self.serial_cx = SerialConnection(port=self.port, baudrate=settings.MESHCORE_BAUD_RATE)
            self.mc = MeshCore(cx=self.serial_cx)
            await self.mc.connect()
            logger.info(f"Connected to MeshCore radio on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to radio: {e}")
            return False

    async def disconnect(self):
        """Close serial connection."""
        if self.mc:
            await self.mc.disconnect()
            self.mc = None
        self.serial_cx = None

    async def get_current_signal(self, target_node):
        """
        Get current signal strength by sending a trace to the target node.

        Args:
            target_node: Node model instance with mesh_identity

        Returns:
            dict with snr and optional rssi, or None if unavailable
        """
        if not self.mc:
            logger.error("Radio not connected")
            return None

        try:
            # Extract short hash (first 2 chars) from mesh_identity for trace path
            # mesh_identity is like "46381bfb67f7..." we need "46"
            node_hash = target_node.mesh_identity[:2]
            logger.info(f"Sending trace to node {target_node.name} (hash: {node_hash})")

            # Subscribe to trace data events
            trace_received = asyncio.Event()
            trace_data = {}
            trace_start_time = time.time()

            async def on_trace_data(event):
                logger.info(f"Trace data received: {event.payload}")
                trace_data["payload"] = event.payload
                trace_received.set()

            subscription = self.mc.subscribe(EventType.TRACE_DATA, on_trace_data)
            logger.info(f"Subscribed to TRACE_DATA events")

            try:
                # Send trace command
                logger.info(f"Sending trace command with path: {node_hash}")
                await self.mc.commands.send_trace(path=node_hash)
                logger.info(f"Trace command sent, waiting for response...")

                # Wait for trace response (with timeout)
                await asyncio.wait_for(trace_received.wait(), timeout=10.0)
                trace_duration = time.time() - trace_start_time
                logger.info(f"Trace response received! Duration: {trace_duration:.2f}s")

                # Extract signal data from trace response
                payload = trace_data.get("payload", {})
                path = payload.get("path", [])

                if len(path) >= 2:
                    # path[0] = SNR at target repeater (our signal reaching it)
                    # path[1] = SNR at our device (repeater's signal reaching us)
                    snr_to_target = path[0].get("snr")
                    snr_from_target = path[1].get("snr")

                    return {
                        "snr_to_target": snr_to_target,
                        "snr_from_target": snr_from_target,
                    }
                else:
                    logger.warning(f"Insufficient path data in trace response: {len(path)} nodes")
                    return None

            finally:
                subscription.unsubscribe()

        except asyncio.TimeoutError:
            trace_duration = time.time() - trace_start_time
            logger.error(f"Timeout waiting for trace response after {trace_duration:.2f}s")
            return None
        except Exception as e:
            logger.error(f"Failed to read signal from radio: {e}")
            return None

    async def __aenter__(self):
        """Async context manager support."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager support."""
        await self.disconnect()


# Global radio instance for WebSocket consumer to use
_radio_instance = None
_radio_lock = asyncio.Lock()


async def get_radio_interface():
    """
    Get or create global radio interface instance.

    Returns:
        RadioInterface instance
    """
    global _radio_instance

    async with _radio_lock:
        if _radio_instance is None:
            _radio_instance = RadioInterface()
            await _radio_instance.connect()

        return _radio_instance
