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

from metro.models import FieldTest, Trace, Node
from metro.radio import RadioInterface

logger = logging.getLogger(__name__)


class SignalStreamConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for GPS and signal data streaming.

    Message types from phone:
    - gps_data: GPS coordinates from phone
    - request_measurement: Request to save a measurement
    - radio_status_request: Request to check radio connection status

    Message types to phone:
    - radio_status: Radio connection status (connected: bool, error: str)
    - signal_data: Current signal strength from radio
    - measurement_saved: Confirmation of saved measurement
    - error: Error message
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_gps = None
        self.current_signal = None
        self.radio = None

    async def connect(self):
        """Accept WebSocket connection from phone."""
        await self.accept()
        logger.info("Phone connected to WebSocket")

        # Initialize radio connection
        self.radio = RadioInterface()
        radio_connected = await self.radio.connect()

        # Send welcome message
        await self.send(text_data=json.dumps({"type": "connected", "message": "Connected to Pi"}))

        # Immediately send radio status after websocket connects
        await self.send_radio_status(radio_connected)

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.radio:
            await self.radio.disconnect()
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
            elif message_type == "radio_status_request":
                await self.handle_radio_status_request()
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
            logger.debug(f"Received GPS data packet: {gps_data}")
            self.current_gps = {
                "latitude": gps_data.get("latitude"),
                "longitude": gps_data.get("longitude"),
                "altitude": gps_data.get("altitude"),
                "accuracy": gps_data.get("accuracy"),
                "timestamp": gps_data.get("timestamp"),
            }
        except Exception as e:
            logger.error(f"Error handling GPS data: {e}")
            await self.send_error(f"GPS data error: {e}")

    async def handle_measurement_request(self, message):
        """
        Handle request to save a trace measurement.

        Combines current GPS data with signal data from radio and saves to database.

        Args:
            message: dict with field_test_id (FieldTest ID)
        """
        try:
            field_test_id = message.get("field_test_id")

            if not field_test_id:
                await self.send_error("Missing field_test_id")
                return

            if not self.current_gps:
                await self.send_error("No GPS data available")
                return

            # Verify field test exists and is active
            field_test = await self.get_field_test(field_test_id)
            if not field_test:
                await self.send_error(f"Field test {field_test_id} not found")
                return

            if not field_test["is_active"]:
                await self.send_error(f"Field test {field_test_id} is not active")
                return

            # Read current signal data from radio
            signal_data = await self.get_signal_from_radio(field_test["target_node_id"])

            # Always save trace, even if trace failed
            if not signal_data:
                logger.warning("Trace failed, saving trace with default values")
                signal_data = {
                    "snr_to_target": 0.0,
                    "snr_from_target": 0.0,
                }
                trace_success = False
            else:
                trace_success = True

            # Save trace to database
            trace_id = await self.save_trace(
                field_test_id=field_test_id,
                gps_data=self.current_gps,
                signal_data=signal_data,
                trace_success=trace_success,
            )

            # Send confirmation to phone
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "measurement_saved",
                        "trace_id": trace_id,
                        "snr_to_target": signal_data["snr_to_target"],
                        "snr_from_target": signal_data["snr_from_target"],
                        "latitude": self.current_gps["latitude"],
                        "longitude": self.current_gps["longitude"],
                    }
                )
            )

            logger.info(f"Trace saved: {trace_id}")

        except Exception as e:
            logger.error(f"Error handling measurement request: {e}")
            await self.send_error(f"Failed to save trace: {e}")

    async def get_signal_from_radio(self, target_node_id):
        """
        Read current signal data from MeshCore radio using trace command.

        Args:
            target_node_id: ID of target node to get signal for

        Returns:
            dict with rssi and snr, or None if unavailable
        """
        try:
            # Get target node from database
            target_node = await database_sync_to_async(Node.objects.get)(id=target_node_id)

            if not self.radio:
                logger.error("Radio not initialized")
                return None

            # Get signal data via trace command
            signal_data = await self.radio.get_current_signal(target_node)
            return signal_data
        except Exception as e:
            logger.error(f"Failed to read signal from radio: {e}")
            return None

    @database_sync_to_async
    def get_field_test(self, field_test_id):
        """
        Get field test from database.

        Args:
            field_test_id: FieldTest ID

        Returns:
            dict with field test info or None if not found
        """
        try:
            field_test = FieldTest.objects.get(id=field_test_id)
            return {
                "id": field_test.id,
                "target_node_id": field_test.target_node.id,
                "is_active": field_test.is_active,
            }
        except FieldTest.DoesNotExist:
            return None

    @database_sync_to_async
    def save_trace(self, field_test_id, gps_data, signal_data, trace_success):
        """
        Save trace to database.

        Args:
            field_test_id: FieldTest ID
            gps_data: GPS coordinates and metadata
            signal_data: SNR values
            trace_success: Whether the trace succeeded

        Returns:
            Trace ID
        """
        try:
            # Get field test
            field_test = FieldTest.objects.get(id=field_test_id)

            # Create Point for location
            location = Point(gps_data["longitude"], gps_data["latitude"], srid=4326)

            # Create trace
            trace = Trace.objects.create(
                field_test=field_test,
                location=location,
                altitude=gps_data.get("altitude"),
                gps_accuracy=gps_data.get("accuracy"),
                snr_to_target=signal_data["snr_to_target"],
                snr_from_target=signal_data["snr_from_target"],
                trace_success=trace_success,
            )

            return trace.id

        except FieldTest.DoesNotExist:
            msg = f"Field test {field_test_id} not found"
            raise ValueError(msg)
        except Exception as e:
            logger.error(f"Database error saving trace: {e}")
            raise

    async def handle_radio_status_request(self):
        """Handle request to check radio connection status."""
        try:
            if not self.radio:
                await self.send_radio_status(False, "Radio not initialized")
                return

            # Check if radio is connected and responding
            is_connected = await self.radio.check_connection()
            await self.send_radio_status(is_connected)

        except Exception as e:
            logger.error(f"Error checking radio status: {e}")
            await self.send_radio_status(False, str(e))

    async def send_radio_status(self, is_connected, error_message=None):
        """
        Send radio connection status to phone.

        Args:
            is_connected: bool - whether radio is connected
            error_message: str - error details if disconnected
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "radio_status",
                    "connected": is_connected,
                    "error": error_message,
                }
            )
        )
        logger.info(f"Sent radio status: connected={is_connected}, error={error_message}")

    async def send_error(self, message):
        """Send error message to phone."""
        await self.send(text_data=json.dumps({"type": "error", "message": message}))

    async def send_signal_update(self, signal_data):
        """
        Send signal update to phone.

        This can be called by background services to push real-time signal data.

        Args:
            signal_data: dict with snr_to_target, snr_from_target, timestamp
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "signal_data",
                    "snr_to_target": signal_data["snr_to_target"],
                    "snr_from_target": signal_data["snr_from_target"],
                    "timestamp": signal_data["timestamp"],
                }
            )
        )
