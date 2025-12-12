"""
Simple interface for reading signal data from MeshCore radio.

Used by Signal Mapper WebSocket consumer for on-demand signal readings.
"""

import logging
import serial
import meshcore
from django.conf import settings

logger = logging.getLogger(__name__)


class RadioInterface:
    """
    Simple interface to read current signal data from MeshCore radio.
    """

    def __init__(self, port=None):
        """
        Initialize radio interface.

        Args:
            port: Serial port path (default from settings)
        """
        self.port = port or settings.MESHCORE_SERIAL_PORT
        self.serial = None
        self.radio = None
        logger.info(f"Radio interface on {self.port}")

    def connect(self):
        """Open serial connection to radio."""
        try:
            self.serial = serial.Serial(self.port, settings.MESHCORE_BAUD_RATE, timeout=1)

            # Initialize MeshCore radio connection
            self.radio = meshcore.Radio(self.serial)
            logger.info(f"Connected to MeshCore radio on {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to radio: {e}")
            return False

    def disconnect(self):
        """Close serial connection."""
        if self.radio:
            self.radio = None

        if self.serial:
            self.serial.close()
            self.serial = None

    def get_current_signal(self, target_node_id=None):
        """
        Get current signal strength from radio.

        Args:
            target_node_id: ID of target node (optional, for filtering stats)

        Returns:
            dict with rssi and snr, or None if unavailable
        """
        if not self.radio:
            logger.error("Radio not connected")
            return None

        try:
            # Get stats from MeshCore radio
            # The meshcore library should provide getStats() or similar
            # Adjust based on actual API
            stats = self.radio.getStats()

            # Extract RSSI and SNR from stats
            # Adjust field names based on actual meshcore library response
            return {"rssi": stats.get("last_rssi") or stats.get("rssi"), "snr": stats.get("last_snr") or stats.get("snr")}

        except Exception as e:
            logger.error(f"Failed to read signal from radio: {e}")
            return None

    def __enter__(self):
        """Context manager support."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager support."""
        self.disconnect()


# Global radio instance for WebSocket consumer to use
_radio_instance = None


def get_radio_interface():
    """
    Get or create global radio interface instance.

    Returns:
        RadioInterface instance
    """
    global _radio_instance

    if _radio_instance is None:
        _radio_instance = RadioInterface()
        _radio_instance.connect()

    return _radio_instance
