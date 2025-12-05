from rest_framework_gis.serializers import GeoFeatureModelSerializer
from rest_framework import serializers
from max.models import Node, SignalMeasurement, Role


class NodeSerializer(GeoFeatureModelSerializer):
    """
    Serializer for Node model with GeoJSON support.
    Used for listing repeaters available for testing.
    """

    class Meta:
        model = Node
        geo_field = "location"
        fields = ["id", "name", "mesh_identity", "role", "is_active", "last_seen", "location"]


class SignalMeasurementSerializer(GeoFeatureModelSerializer):
    """
    Serializer for SignalMeasurement model with GeoJSON support.
    Handles signal strength measurements from field collection.
    """

    class Meta:
        model = SignalMeasurement
        geo_field = "location"
        fields = [
            "id",
            "location",
            "altitude",
            "gps_accuracy",
            "target_node",
            "rssi",
            "snr",
            "timestamp",
            "session_id",
            "collector_user",
        ]
        read_only_fields = ["id", "timestamp"]
