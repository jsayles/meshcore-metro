from django.shortcuts import render


def signal_mapper(request):
    """Render the main signal mapping interface"""
    return render(request, "max/signal_mapper.html")
