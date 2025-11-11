from django.contrib import admin
from .models import Node, RepeaterStats, NeighbourInfo, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_active', 'date_joined']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['-date_joined']


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'mesh_identity', 'role', 'owner', 'is_active', 'last_seen']
    list_filter = ['role', 'is_active', 'firmware_version']
    search_fields = ['name', 'mesh_identity', 'public_key', 'description']
    readonly_fields = ['first_seen', 'last_seen']
    fieldsets = [
        ('Identity', {
            'fields': ['mesh_identity', 'public_key', 'firmware_version', 'role']
        }),
        ('Information', {
            'fields': ['name', 'description', 'owner']
        }),
        ('Location', {
            'fields': ['latitude', 'longitude', 'altitude'],
            'classes': ['collapse']
        }),
        ('Status', {
            'fields': ['is_active', 'first_seen', 'last_seen']
        }),
    ]


@admin.register(RepeaterStats)
class RepeaterStatsAdmin(admin.ModelAdmin):
    list_display = ['node', 'timestamp', 'battery_voltage', 'last_rssi', 'last_snr', 'n_packets_recv', 'n_packets_sent']
    list_filter = ['timestamp', 'node']
    search_fields = ['node__name', 'node__mesh_identity']
    readonly_fields = ['timestamp', 'battery_voltage']
    date_hierarchy = 'timestamp'
    fieldsets = [
        ('Node', {
            'fields': ['node', 'timestamp']
        }),
        ('Power', {
            'fields': ['batt_milli_volts', 'battery_voltage']
        }),
        ('Signal Quality', {
            'fields': ['noise_floor', 'last_rssi', 'last_snr', 'curr_tx_queue_len']
        }),
        ('Packet Statistics', {
            'fields': [
                'n_packets_recv', 'n_packets_sent',
                'n_recv_flood', 'n_recv_direct',
                'n_sent_flood', 'n_sent_direct',
                'n_flood_dups', 'n_direct_dups'
            ],
            'classes': ['collapse']
        }),
        ('Time Metrics', {
            'fields': ['total_air_time_secs', 'total_rx_air_time_secs', 'total_up_time_secs']
        }),
        ('Errors', {
            'fields': ['err_events']
        }),
    ]


@admin.register(NeighbourInfo)
class NeighbourInfoAdmin(admin.ModelAdmin):
    list_display = ['node', 'neighbour', 'snr', 'last_updated']
    list_filter = ['last_updated', 'node']
    search_fields = ['node__name', 'node__mesh_identity', 'neighbour__name', 'neighbour__mesh_identity']
    readonly_fields = ['last_updated']
    fieldsets = [
        ('Relationship', {
            'fields': ['node', 'neighbour']
        }),
        ('Timestamps', {
            'fields': ['advert_timestamp', 'heard_timestamp', 'last_updated']
        }),
        ('Signal Quality', {
            'fields': ['snr']
        }),
    ]
