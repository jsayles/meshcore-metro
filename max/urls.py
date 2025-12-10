from django.contrib import admin
from django.urls import path, include
from max import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("api.urls")),
    path("", views.mesh_home, name="home"),
    path("node/<int:node_id>/", views.node_detail, name="node_detail"),
    path("mapper/", views.signal_mapper, name="signal_mapper"),
]
