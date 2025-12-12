from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from metro.models import Node, MappingSession, Trace, Role
from .serializers import NodeSerializer, MappingSessionSerializer, TraceSerializer


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


class MappingSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for mapping sessions.
    Supports creating, updating, and retrieving mapping sessions.
    """

    queryset = MappingSession.objects.all().select_related("target_node")
    serializer_class = MappingSessionSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["target_node", "end_time"]
    ordering_fields = ["start_time"]
    ordering = ["-start_time"]


class TraceViewSet(viewsets.ModelViewSet):
    """
    API endpoint for trace measurements.
    Supports creating new traces and retrieving for heatmap display.
    """

    queryset = Trace.objects.all().select_related("session__target_node")
    serializer_class = TraceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["session", "session__target_node"]
    ordering_fields = ["timestamp"]
    ordering = ["-timestamp"]
