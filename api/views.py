from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from max.models import Node, SignalMeasurement, Role
from .serializers import NodeSerializer, SignalMeasurementSerializer


class NodeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for listing Nodes.
    Read-only - used for node overview and selecting target repeaters in frontend.
    """

    queryset = Node.objects.all().order_by("name")
    serializer_class = NodeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active", "role"]
    search_fields = ["name", "mesh_identity"]
    ordering_fields = ["name", "last_seen"]


class SignalMeasurementViewSet(viewsets.ModelViewSet):
    """
    API endpoint for signal measurements.
    Supports creating new measurements and retrieving for heatmap display.
    """

    queryset = SignalMeasurement.objects.all().select_related("target_node")
    serializer_class = SignalMeasurementSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["target_node", "session_id"]
    ordering_fields = ["timestamp", "rssi", "snr"]
    ordering = ["-timestamp"]
