"""
Simple interface for reading signal data from MeshCore radio.

Used by Signal Mapper WebSocket consumer for on-demand signal readings.
"""

import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import serial and meshcore libraries
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available, using mock mode")

try:
    import meshcore
    MESHCORE_AVAILABLE = True
except ImportError:
    MESHCORE_AVAILABLE = False
    logger.warning("meshcore library not available, using mock mode")


class RadioInterface:
    """
    Simple interface to read current signal data from MeshCore radio.

    Supports both real radio (via meshcore library) and mock mode for testing.
    """

    def __init__(self, port=None, use_mock=None):
        """
        Initialize radio interface.

        Args:
            port: Serial port path (default from settings)
            use_mock: Use mock data instead of real radio (default from settings)
        """
        self.port = port or settings.MESHCORE_SERIAL_PORT

        # Use mock if explicitly requested, or if libraries unavailable, or if setting says so
        if use_mock is None:
            self.use_mock = settings.MESHCORE_USE_MOCK or not (SERIAL_AVAILABLE and MESHCORE_AVAILABLE)
        else:
            self.use_mock = use_mock

        self.serial = None
        self.radio = None

        if self.use_mock:
            logger.info("Radio interface in MOCK mode")
        else:
            logger.info(f"Radio interface on {self.port} (REAL mode)")

    def connect(self):
        """Open serial connection to radio."""
        if self.use_mock:
            return True

        try:
            self.serial = serial.Serial(
                self.port,
                settings.MESHCORE_BAUD_RATE,
                timeout=1
            )

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
        if self.use_mock:
            return self._get_mock_signal()

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
            return {
                "rssi": stats.get("last_rssi") or stats.get("rssi"),
                "snr": stats.get("last_snr") or stats.get("snr")
            }

        except Exception as e:
            logger.error(f"Failed to read signal from radio: {e}")
            return None

    def _get_mock_signal(self):
        """Generate mock signal data for testing."""
        import random

        return {
            "rssi": random.randint(-100, -40),
            "snr": random.randint(-5, 15)
        }

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
