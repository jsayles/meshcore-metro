"""
Load contacts from USB radio into database.
Usage: python manage.py load_radio_data
"""
import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from max.models import Node

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
            default="/dev/tty.usbmodem21401",
            help="Serial port (default: /dev/tty.usbmodem21401)",
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
            public_key = contact.get('public_key', '')
            if not public_key:
                continue

            mesh_identity = contact.get('mesh_identity', public_key[:16])

            node, created = await sync_to_async(Node.objects.update_or_create)(
                mesh_identity=mesh_identity,
                defaults={
                    'public_key': public_key,
                    'name': contact.get('adv_name', ''),
                    'role': contact.get('role', 0),
                    'last_seen': timezone.now(),
                }
            )

            status = "Created" if created else "Updated"
            self.stdout.write(f"  {status}: {node.name or mesh_identity}")
