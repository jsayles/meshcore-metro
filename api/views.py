import asyncio
import logging
import time

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.utils import timezone

from api.serializers import NodeSerializer

from metro.models import Node, Role
from metro.subsystems import lora_radio

logger = logging.getLogger(__name__)


class NodeViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing Nodes.
    Supports CRUD operations plus discovery endpoint.
    """

    queryset = Node.objects.all().order_by("name")
    serializer_class = NodeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "role"]
    search_fields = ["name", "mesh_identity"]
    ordering_fields = ["name", "last_seen"]

    @action(detail=False, methods=["post"])
    def discover(self, request):
        """
        Discover all repeaters from radio, excluding ones already in database.
        Returns transient discovery results (not saved to database).
        """
        try:

            async def run_discovery():
                radio = lora_radio.RadioInterface()
                await radio.connect()
                try:
                    timeout = request.data.get("timeout", 30)
                    discovered = await radio.discover_nodes(timeout=timeout)
                    return discovered
                finally:
                    await radio.disconnect()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                discovered_nodes = loop.run_until_complete(run_discovery())
            finally:
                loop.close()

            # Filter out nodes already in database
            existing_mesh_ids = set(Node.objects.filter(role=Role.REPEATER).values_list("mesh_identity", flat=True))
            filtered_nodes = [node for node in discovered_nodes if node["mesh_identity"] not in existing_mesh_ids]

            return Response({"count": len(filtered_nodes), "nodes": filtered_nodes})

        except Exception as e:
            logger.error(f"Node discovery failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to discover nodes. Please check radio connection."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def ping(self, request, pk=None):
        """
        Ping a node by sending a trace command and waiting for a response.
        Updates last_seen on success.
        """
        node = self.get_object()

        try:

            async def run_ping():
                radio = lora_radio.RadioInterface()
                await radio.connect()
                try:
                    start = time.monotonic()
                    result = await radio.get_current_signal(node)
                    elapsed_ms = round((time.monotonic() - start) * 1000)
                    return result, elapsed_ms
                finally:
                    await radio.disconnect()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                signal, elapsed_ms = loop.run_until_complete(run_ping())
            finally:
                loop.close()

            if signal is None:
                return Response({"reachable": False, "error": "No response (timeout)"})

            Node.objects.filter(pk=node.pk).update(last_seen=timezone.now())
            return Response(
                {
                    "reachable": True,
                    "snr_to_target": signal.get("snr_to_target"),
                    "snr_from_target": signal.get("snr_from_target"),
                    "latency_ms": elapsed_ms,
                }
            )

        except Exception as e:
            logger.error(f"Ping failed for node {node}: {e}", exc_info=True)
            return Response(
                {"error": "Radio connection failed. Check the radio is connected."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

    @action(detail=False, methods=["post"])
    def add_node(self, request):
        """
        Add a discovered node to the database.
        Expects discovery data in request body.
        """
        try:
            data = request.data
            mesh_identity = data.get("mesh_identity")

            node, created = Node.objects.get_or_create(
                mesh_identity=mesh_identity,
                defaults={
                    "public_key": data.get("pubkey", ""),
                    "name": data.get("name", ""),
                    "role": Role.CLIENT if data.get("node_type") == 1 else Role.REPEATER,
                    "last_seen": timezone.now(),
                },
            )

            if not created:
                return Response({"error": "Node already exists"}, status=status.HTTP_400_BAD_REQUEST)

            lat = data.get("lat")
            lon = data.get("lon")
            if lat and lon:
                node.location = Point(lon, lat, srid=4326)
                node.save()

            serializer = self.get_serializer(node)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Failed to add node: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to add node. Please verify the data and try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
