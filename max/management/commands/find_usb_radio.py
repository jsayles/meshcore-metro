"""
Django management command to find connected MeshCore radios.

Usage:
    python manage.py find_usb_radio
    python manage.py find_usb_radio --test
    python manage.py find_usb_radio --update-env
"""

from django.core.management.base import BaseCommand
from django.conf import settings

try:
    import serial.tools.list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

try:
    import meshcore

    MESHCORE_AVAILABLE = True
except ImportError:
    MESHCORE_AVAILABLE = False


class Command(BaseCommand):
    help = "Find connected MeshCore radios and test connection"

    def add_arguments(self, parser):
        parser.add_argument("--test", action="store_true", help="Test connection to found radios")
        parser.add_argument("--update-env", action="store_true", help="Update .env file with found radio port")

    def handle(self, *args, **options):
        if not SERIAL_AVAILABLE:
            self.stdout.write(self.style.ERROR("pyserial not installed. Install with: uv add pyserial"))
            return

        self.stdout.write(self.style.SUCCESS("🔍 Searching for USB serial devices...\n"))

        # List all serial ports
        ports = list(serial.tools.list_ports.comports())

        if not ports:
            self.stdout.write(self.style.WARNING("No USB serial devices found."))
            self.stdout.write("\nMake sure your MeshCore radio is:")
            self.stdout.write("  • Plugged in via USB")
            self.stdout.write("  • Powered on")
            self.stdout.write("  • Using a data-capable USB cable (not charge-only)")
            return

        # Display all ports
        self.stdout.write(f"Found {len(ports)} USB serial device(s):\n")

        likely_radios = []

        for i, port in enumerate(ports, 1):
            # Check if it looks like a MeshCore radio
            is_likely = self._is_likely_meshcore(port)

            marker = "✓" if is_likely else " "
            style = self.style.SUCCESS if is_likely else self.style.WARNING

            self.stdout.write(style(f"[{marker}] {i}. {port.device}"))
            self.stdout.write(f"    Description: {port.description}")
            if port.manufacturer:
                self.stdout.write(f"    Manufacturer: {port.manufacturer}")
            if port.serial_number:
                self.stdout.write(f"    Serial: {port.serial_number}")
            self.stdout.write("")

            if is_likely:
                likely_radios.append(port)

        # Suggest likely candidates
        if likely_radios:
            self.stdout.write(self.style.SUCCESS(f"\n🎯 {len(likely_radios)} device(s) look like MeshCore radios:\n"))
            for port in likely_radios:
                self.stdout.write(self.style.SUCCESS(f"   {port.device}"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  No obvious MeshCore radios found. Try testing each device manually."))

        # Test connection if requested
        if options["test"]:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("🧪 Testing connections...\n"))

            test_ports = likely_radios if likely_radios else ports

            for port in test_ports:
                self.test_connection(port.device)

        # Show .env update instructions
        if likely_radios:
            primary = likely_radios[0]
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write(self.style.SUCCESS("📝 To use this radio:\n"))
            self.stdout.write(f"1. Update your .env file:")
            self.stdout.write(f"   SERIAL_PORT={primary.device}\n")
            self.stdout.write(f"2. Restart your server:")
            self.stdout.write(f"   uv run daphne -b 0.0.0.0 -p 8000 max.asgi:application")

            if options["update_env"]:
                self.update_env_file(primary.device)

    def _is_likely_meshcore(self, port):
        """
        Heuristic to detect if a port is likely a MeshCore radio.

        Adjust these patterns based on your actual hardware.
        """
        device = port.device.lower()
        desc = port.description.lower()
        manufacturer = (port.manufacturer or "").lower()

        # Common patterns for MeshCore radios
        patterns = [
            "meshcore" in desc,
            "meshcore" in manufacturer,
            "esp32" in desc,
            "cp210" in desc,  # Common USB-UART chip
            "ch340" in desc,  # Common USB-UART chip
            "ftdi" in desc,  # FTDI USB-UART
            "/dev/tty.usbmodem" in device,  # Mac pattern
            "/dev/ttyacm" in device,  # Linux pattern
            "/dev/ttyusb" in device,  # Linux pattern
        ]

        return any(patterns)

    def test_connection(self, port):
        """Test connection to a specific port."""
        self.stdout.write(f"\n🔌 Testing {port}...")

        if not MESHCORE_AVAILABLE:
            self.stdout.write(self.style.WARNING("   meshcore library not available, skipping connection test"))
            return

        try:
            import serial

            # Try to open the port
            ser = serial.Serial(port, settings.MESHCORE_BAUD_RATE, timeout=2)

            self.stdout.write(self.style.SUCCESS(f"   ✓ Port opened successfully at {settings.MESHCORE_BAUD_RATE} baud"))

            # Try to initialize MeshCore radio
            try:
                radio = meshcore.Radio(ser)
                self.stdout.write(self.style.SUCCESS("   ✓ MeshCore radio initialized"))

                # Try to get stats
                try:
                    stats = radio.getStats()
                    self.stdout.write(self.style.SUCCESS("   ✓ Successfully read stats from radio"))
                    if hasattr(stats, "last_rssi"):
                        self.stdout.write(f"      RSSI: {stats.last_rssi} dBm")
                    if hasattr(stats, "last_snr"):
                        self.stdout.write(f"      SNR: {stats.last_snr} dB")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"   ⚠ Could not read stats: {e}"))

                ser.close()

            except Exception as e:
                ser.close()
                self.stdout.write(self.style.ERROR(f"   ✗ Not a MeshCore radio: {e}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ✗ Error: {e}"))

    def update_env_file(self, port):
        """Update .env file with the found port."""
        from pathlib import Path

        env_path = Path(settings.BASE_DIR) / ".env"

        try:
            # Read existing .env
            if env_path.exists():
                with open(env_path, "r") as f:
                    lines = f.readlines()

                # Update SERIAL_PORT line
                updated = False
                for i, line in enumerate(lines):
                    if line.startswith("SERIAL_PORT="):
                        lines[i] = f"SERIAL_PORT={port}\n"
                        updated = True

                if not updated:
                    lines.append(f"\nSERIAL_PORT={port}\n")

                with open(env_path, "w") as f:
                    f.writelines(lines)

                self.stdout.write(self.style.SUCCESS(f"\n✓ Updated {env_path}"))
            else:
                self.stdout.write(self.style.WARNING(f"\n⚠ .env file not found at {env_path}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n✗ Failed to update .env: {e}"))
