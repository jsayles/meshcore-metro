"""
WebSocket consumers for real-time GPS and signal data streaming.

Architecture:
- Phone browser connects via WebSocket
- Phone streams GPS coordinates to Pi
- Pi reads signal data from USB-connected MeshCore radio
- Pi combines GPS + signal data and stores in database
- Pi sends signal updates back to phone for real-time display
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.gis.geos import Point
from asgiref.sync import sync_to_async

from max.models import SignalMeasurement, Node

logger = logging.getLogger(__name__)


class SignalStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for GPS and signal data streaming.

    Message types from phone:
    - gps_data: GPS coordinates from phone
    - request_measurement: Request to save a measurement

    Message types to phone:
    - signal_data: Current signal strength from radio
    - measurement_saved: Confirmation of saved measurement
    - error: Error message
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_gps = None
        self.current_signal = None

    async def connect(self):
        """Accept WebSocket connection from phone."""
        await self.accept()
        logger.info("Phone connected to WebSocket")

        # Send welcome message
        await self.send(text_data=json.dumps({"type": "connected", "message": "Connected to Pi"}))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        logger.info(f"Phone disconnected from WebSocket: {close_code}")

    async def receive(self, text_data):
        """
        Receive message from phone.

        Expected message format:
        {
            "type": "gps_data" | "request_measurement",
            "data": {...}
        }
        """
        try:
            message = json.loads(text_data)
            message_type = message.get("type")

            if message_type == "gps_data":
                await self.handle_gps_data(message.get("data", {}))
            elif message_type == "request_measurement":
                await self.handle_measurement_request(message)
            else:
                logger.warning(f"Unknown message type: {message_type}")

        except json.JSONDecodeError:
            logger.error("Invalid JSON received from phone")
            await self.send_error("Invalid message format")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self.send_error(str(e))

    async def handle_gps_data(self, gps_data):
        """
        Handle GPS data from phone.

        Args:
            gps_data: dict with latitude, longitude, altitude, accuracy, timestamp
        """
        try:
            self.current_gps = {
                "latitude": gps_data.get("latitude"),
                "longitude": gps_data.get("longitude"),
                "altitude": gps_data.get("altitude"),
                "accuracy": gps_data.get("accuracy"),
                "timestamp": gps_data.get("timestamp"),
            }

            logger.debug(f"GPS updated: {self.current_gps['latitude']}, {self.current_gps['longitude']}")

            # TODO: Trigger signal reading from radio here
            # For now, we'll wait for explicit measurement requests
            # In the future, this could automatically combine with radio data

        except Exception as e:
            logger.error(f"Error handling GPS data: {e}")
            await self.send_error(f"GPS data error: {e}")

    async def handle_measurement_request(self, message):
        """
        Handle request to save a measurement.

        Combines current GPS data with signal data from radio and saves to database.

        Args:
            message: dict with target_node_id, session_id
        """
        try:
            target_node_id = message.get("target_node_id")
            session_id = message.get("session_id")

            if not target_node_id or not session_id:
                await self.send_error("Missing target_node_id or session_id")
                return

            if not self.current_gps:
                await self.send_error("No GPS data available")
                return

            # Read current signal data from radio
            signal_data = await self.get_signal_from_radio(target_node_id)

            # Always save measurement, even if trace failed
            if not signal_data:
                logger.warning("Trace failed, saving measurement with default values")
                signal_data = {
                    "snr_to_target": 0.0,
                    "snr_from_target": 0.0,
                }
                trace_success = False
            else:
                trace_success = True

            # Save measurement to database
            measurement_id = await self.save_measurement(
                target_node_id=target_node_id,
                session_id=session_id,
                gps_data=self.current_gps,
                signal_data=signal_data,
                trace_success=trace_success,
            )

            # Send confirmation to phone
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "measurement_saved",
                        "measurement_id": measurement_id,
                        "snr_to_target": signal_data["snr_to_target"],
                        "snr_from_target": signal_data["snr_from_target"],
                        "latitude": self.current_gps["latitude"],
                        "longitude": self.current_gps["longitude"],
                    }
                )
            )

            logger.info(f"Measurement saved: {measurement_id}")

        except Exception as e:
            logger.error(f"Error handling measurement request: {e}")
            await self.send_error(f"Failed to save measurement: {e}")

    async def get_signal_from_radio(self, target_node_id):
        """
        Read current signal data from MeshCore radio using trace command.

        Args:
            target_node_id: ID of target node to get signal for

        Returns:
            dict with rssi and snr, or None if unavailable
        """
        from max.radio_interface import get_radio_interface

        try:
            # Get target node from database
            target_node = await database_sync_to_async(Node.objects.get)(id=target_node_id)

            # Get radio interface (already async)
            radio = await get_radio_interface()

            # Get signal data via trace command
            signal_data = await radio.get_current_signal(target_node)
            return signal_data
        except Exception as e:
            logger.error(f"Failed to read signal from radio: {e}")
            return None

    @database_sync_to_async
    def save_measurement(self, target_node_id, session_id, gps_data, signal_data, trace_success):
        """
        Save measurement to database.

        Args:
            target_node_id: ID of target node
            session_id: Session UUID
            gps_data: GPS coordinates and metadata
            signal_data: SNR values
            trace_success: Whether the trace succeeded

        Returns:
            Measurement ID
        """
        try:
            # Get target node
            target_node = Node.objects.get(id=target_node_id)

            # Create Point for location
            location = Point(gps_data["longitude"], gps_data["latitude"], srid=4326)

            # Create measurement
            measurement = SignalMeasurement.objects.create(
                location=location,
                altitude=gps_data.get("altitude"),
                gps_accuracy=gps_data.get("accuracy"),
                target_node=target_node,
                snr_to_target=signal_data["snr_to_target"],
                snr_from_target=signal_data["snr_from_target"],
                trace_success=trace_success,
                session_id=session_id,
                collector_user=None,  # Anonymous for now
            )

            return measurement.id

        except Node.DoesNotExist:
            raise ValueError(f"Target node {target_node_id} not found")
        except Exception as e:
            logger.error(f"Database error saving measurement: {e}")
            raise

    async def send_error(self, message):
        """Send error message to phone."""
        await self.send(text_data=json.dumps({"type": "error", "message": message}))

    async def send_signal_update(self, signal_data):
        """
        Send signal update to phone.

        This can be called by background services to push real-time signal data.

        Args:
            signal_data: dict with rssi, snr, timestamp
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "signal_data",
                    "rssi": signal_data["rssi"],
                    "snr": signal_data["snr"],
                    "timestamp": signal_data["timestamp"],
                }
            )
        )
