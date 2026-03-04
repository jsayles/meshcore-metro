from rest_framework_gis.serializers import GeoFeatureModelSerializer
from metro.models import Node


class NodeSerializer(GeoFeatureModelSerializer):
    """
    Serializer for Node model with GeoJSON support.
    """

    class Meta:
        model = Node
        geo_field = "location"
        fields = ["id", "name", "mesh_identity", "role", "is_active", "last_seen", "location", "estimated_range"]
