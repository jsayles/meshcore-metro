import asyncio
import logging
import platform

from rest_framework import viewsets, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.utils import timezone

from api.serializers import NodeSerializer, FieldTestSerializer, TraceSerializer, HotspotConfigSerializer

from metro.models import Node, FieldTest, Trace, Role, HotspotConfig
from metro.subsystems import lora_radio, wifi_hotspot

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
            # Run discovery in async context
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

    @action(detail=False, methods=["post"])
    def add_node(self, request):
        """
        Add a discovered node to the database.
        Expects discovery data in request body.
        """
        try:
            data = request.data
            mesh_identity = data.get("mesh_identity")

            # Use get_or_create to avoid race condition
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

            # Add location if provided
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


class FieldTestViewSet(viewsets.ModelViewSet):
    """
    API endpoint for field tests.
    Supports creating, updating, and retrieving field tests.
    """

    queryset = FieldTest.objects.all().select_related("target_node")
    serializer_class = FieldTestSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["target_node", "end_time"]
    ordering_fields = ["start_time"]
    ordering = ["-start_time"]


class TraceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for trace measurements.
    Supports creating new traces and retrieving for heatmap display.
    """

    queryset = Trace.objects.all().select_related("field_test__target_node")
    serializer_class = TraceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["field_test", "field_test__target_node"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]


class HotspotViewSet(viewsets.ViewSet):
    """WiFi hotspot management endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.wifi_manager = wifi_hotspot.get_wifi_manager()
        except wifi_hotspot.UnsupportedPlatformError as e:
            logger.error(f"WiFi hotspot not supported: {e}")
            self.wifi_manager = None

    @action(detail=False, methods=["get"])
    def config(self, request):
        """GET /api/v1/hotspot/config/ - Get current config (no password)"""
        instance = HotspotConfig.get_instance()
        serializer = HotspotConfigSerializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def capabilities(self, request):
        """GET /api/v1/hotspot/capabilities/ - Check what features are available"""
        if not self.wifi_manager:
            return Response({"can_scan": False, "platform": platform.system()})
        return Response({"can_scan": self.wifi_manager.can_scan(), "platform": platform.system()})

    @action(detail=False, methods=["post"])
    def scan(self, request):
        """POST /api/v1/hotspot/scan/ - Scan WiFi networks"""
        if not self.wifi_manager:
            return Response({"error": "WiFi management not supported on this platform"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            networks = self.wifi_manager.scan_networks()
            return Response({"networks": networks, "count": len(networks)})
        except NotImplementedError:
            logger.warning("WiFi scan not implemented on this platform")
            return Response(
                {"error": "Network scanning not available on this platform"}, status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except RuntimeError as e:
            logger.error(f"WiFi scan failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to scan networks. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def configure(self, request):
        """POST /api/v1/hotspot/configure/ - Save SSID/password"""
        ssid = request.data.get("ssid")
        password = request.data.get("password")

        if not ssid or not password:
            return Response({"error": "SSID and password required"}, status=status.HTTP_400_BAD_REQUEST)

        if not self.wifi_manager:
            return Response({"error": "WiFi management not supported on this platform"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Configure platform (no-op on Mac, NetworkManager on Linux)
            self.wifi_manager.configure(ssid, password)

            # Always save to database
            instance = HotspotConfig.get_instance()
            serializer = HotspotConfigSerializer(instance, data={"ssid": ssid, "password": password}, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()

            return Response({"success": True, "message": f"Hotspot configured for {ssid}", "config": serializer.data})
        except serializers.ValidationError:
            # Re-raise validation errors from serializer
            raise
        except RuntimeError as e:
            logger.error(f"WiFi configuration failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to configure WiFi hotspot. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            logger.error(f"Unexpected error during WiFi configuration: {str(e)}", exc_info=True)
            return Response(
                {"error": "An unexpected error occurred. Please try again."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def connect(self, request):
        """POST /api/v1/hotspot/connect/ - Connect to configured hotspot"""
        instance = HotspotConfig.get_instance()
        if not instance.ssid:
            return Response({"error": "No hotspot configured"}, status=status.HTTP_400_BAD_REQUEST)

        if not self.wifi_manager:
            return Response({"error": "WiFi management not supported on this platform"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            self.wifi_manager.connect()
            return Response({"success": True, "message": f"Connected to {instance.ssid}", "ssid": instance.ssid})
        except NotImplementedError:
            logger.warning("WiFi connect not implemented on this platform")
            return Response(
                {"error": "WiFi connection not available on this platform"}, status=status.HTTP_501_NOT_IMPLEMENTED
            )
        except RuntimeError as e:
            logger.error(f"WiFi connection failed: {str(e)}", exc_info=True)
            return Response(
                {"error": "Failed to connect to WiFi hotspot. Please verify the credentials and try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def status(self, request):
        """GET /api/v1/hotspot/status/ - Check connection status"""
        instance = HotspotConfig.get_instance()

        if not self.wifi_manager:
            return Response(
                {
                    "configured": bool(instance.ssid),
                    "ssid": instance.ssid if instance.ssid else None,
                    "connected": False,
                    "error": "Platform not supported",
                    "platform_support": False,
                    "last_check": None,
                }
            )

        nm_status = self.wifi_manager.check_status()
        return Response(
            {
                "configured": bool(instance.ssid),
                "ssid": instance.ssid if instance.ssid else None,
                "connected": nm_status.get("connected", False),
                "error": nm_status.get("error"),
                "platform_support": nm_status.get("platform_support", True),
                "last_check": nm_status.get("last_check"),
            }
        )
