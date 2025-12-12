from rest_framework.routers import DefaultRouter
from .views import NodeViewSet, MappingSessionViewSet, TraceViewSet

router = DefaultRouter()
router.register(r"nodes", NodeViewSet, basename="node")
router.register(r"sessions", MappingSessionViewSet, basename="session")
router.register(r"traces", TraceViewSet, basename="trace")

urlpatterns = router.urls
