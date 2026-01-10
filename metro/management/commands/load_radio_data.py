"""
Update existing nodes in database with latest data from USB radio.
Does NOT add new nodes - use the mesh_config UI to add nodes.
Usage: python manage.py load_radio_data
"""

import asyncio

from asgiref.sync import sync_to_async

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from metro.models import Node, Role
from metro.subsystems import lora_radio


class Command(BaseCommand):
    help = "Update existing nodes with latest data from USB radio (does not add new nodes)"

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

        radio = lora_radio.RadioInterface(port=port)

        try:
            connection_successful = await radio.connect()
            if not connection_successful:
                msg = f"Failed to connect to radio on {port}"
                raise CommandError(msg)

            self.stdout.write(self.style.SUCCESS("Connected"))

            # Get contacts
            contacts = await radio.get_all_contacts()
            await self.update_radio_data(contacts)

            self.stdout.write(self.style.SUCCESS("Done"))

        finally:
            await radio.disconnect()

    async def update_radio_data(self, contacts_data):
        """Update existing nodes with latest data from radio"""
        if not contacts_data:
            self.stdout.write("No contacts found")
            return

        # Get all existing nodes in database
        existing_nodes = await sync_to_async(list)(Node.objects.all().values_list("mesh_identity", flat=True))
        existing_set = set(existing_nodes)

        self.stdout.write(f"Found {len(contacts_data)} contacts on radio")
        self.stdout.write(f"Found {len(existing_nodes)} nodes in our mesh")

        for key, contact in contacts_data.items():
            public_key = contact.get("public_key", "")
            if not public_key:
                continue

            mesh_identity = public_key[:16]

            # Only update nodes that already exist in database
            if mesh_identity not in existing_set:
                continue

            # Map firmware type to role: Client (1) stays Client, everything else becomes Repeater
            firmware_type = contact.get("type", 0)
            role = Role.CLIENT if firmware_type == 1 else Role.REPEATER

            # Prepare update data
            update_data = {
                "public_key": public_key,
                "name": contact.get("adv_name", ""),
                "role": role,
                "last_seen": timezone.now(),
            }

            # Add location if advertised (non-zero lat/lon)
            adv_lat = contact.get("adv_lat", 0)
            adv_lon = contact.get("adv_lon", 0)
            if adv_lat != 0 or adv_lon != 0:
                update_data["location"] = Point(adv_lon, adv_lat, srid=4326)

            # Update existing node
            await sync_to_async(Node.objects.filter(mesh_identity=mesh_identity).update)(**update_data)

            location_info = f" (lat: {adv_lat:.6f}, lon: {adv_lon:.6f})" if update_data.get("location") else ""
            self.stdout.write(f"  Updated: {contact.get('adv_name', mesh_identity)}{location_info}")
