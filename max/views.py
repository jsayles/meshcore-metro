from django.shortcuts import render, get_object_or_404
import uuid
from .models import Node


def mesh_home(request):
    """Render the network overview map showing all nodes"""
    return render(request, "max/mesh_home.html")


def node_detail(request, node_id):
    """Render detailed view of a specific node"""
    node = get_object_or_404(Node, id=node_id)
    return render(request, "max/node_detail.html", {"node": node})


def signal_mapper(request):
    """Render the signal mapping interface"""
    # Sessions are now created explicitly via API when user starts mapping
    return render(request, "max/signal_mapper.html")
