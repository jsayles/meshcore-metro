"""
Load contacts from USB radio into database.
Usage: python manage.py load_radio_data
"""

import asyncio
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from max.models import Node, Role

try:
    from meshcore import MeshCore, SerialConnection
except ImportError:
    raise CommandError("meshcore library not found")


class Command(BaseCommand):
    help = "Load contacts from USB radio into database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--port",
            type=str,
            default=settings.MESHCORE_SERIAL_PORT,
            help=f"Serial port (default: {settings.MESHCORE_SERIAL_PORT})",
        )

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(*args, **options))

    async def async_handle(self, *args, **options):
        port = options["port"]

        self.stdout.write(f"Connecting to {port}...")

        serial_cx = SerialConnection(port=port, baudrate=115200)
        mc = MeshCore(cx=serial_cx)

        try:
            await mc.connect()
            self.stdout.write(self.style.SUCCESS("Connected"))

            # Get contacts
            await mc.ensure_contacts()
            await self.store_contacts(mc.contacts)

            self.stdout.write(self.style.SUCCESS("Done"))

        finally:
            await mc.disconnect()

    async def store_contacts(self, contacts_data):
        """Store contacts as Node instances"""
        if not contacts_data:
            self.stdout.write("No contacts found")
            return

        self.stdout.write(f"Processing {len(contacts_data)} contacts...")

        for key, contact in contacts_data.items():
            public_key = contact.get("public_key", "")
            if not public_key:
                continue

            mesh_identity = contact.get("mesh_identity", public_key[:16])

            # Map firmware type to role: Client (1) stays Client, everything else becomes Repeater
            firmware_type = contact.get("type", 0)
            role = Role.CLIENT if firmware_type == 1 else Role.REPEATER

            # Prepare location data if available
            defaults = {
                "public_key": public_key,
                "name": contact.get("adv_name", ""),
                "role": role,
                "last_seen": timezone.now(),
            }

            # Add location if advertised (non-zero lat/lon)
            adv_lat = contact.get("adv_lat", 0)
            adv_lon = contact.get("adv_lon", 0)
            if adv_lat != 0 or adv_lon != 0:
                defaults["location"] = Point(adv_lon, adv_lat, srid=4326)

            node, created = await sync_to_async(Node.objects.update_or_create)(
                mesh_identity=mesh_identity,
                defaults=defaults,
            )

            status = "Created" if created else "Updated"
            location_info = f" (lat: {adv_lat:.6f}, lon: {adv_lon:.6f})" if defaults.get("location") else ""
            self.stdout.write(f"  {status}: {node.name or mesh_identity}{location_info}")
