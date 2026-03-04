"""
WebSocket consumers for real-time mesh monitoring.
"""

import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class MonitoringConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time mesh node monitoring.
    Placeholder — full implementation coming with monitoring dashboard.
    """

    async def connect(self):
        await self.channel_layer.group_add("monitoring", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("monitoring", self.channel_name)
