from django.shortcuts import render, get_object_or_404
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
    # Ensure session is created
    if not request.session.session_key:
        request.session.create()

    context = {"session_id": request.session.session_key}
    return render(request, "max/signal_mapper.html", context)
