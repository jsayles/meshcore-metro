from rest_framework.routers import DefaultRouter
from .views import NodeViewSet, SignalMeasurementViewSet

router = DefaultRouter()
router.register(r"nodes", NodeViewSet, basename="node")
router.register(r"measurements", SignalMeasurementViewSet, basename="measurement")

urlpatterns = router.urls
