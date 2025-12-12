from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Node, RepeaterStats, NeighbourInfo, MappingSession, Trace, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "first_name", "last_name", "is_staff", "is_active"]
    list_filter = ["is_staff", "is_active", "date_joined"]
    search_fields = ["username", "email", "first_name", "last_name"]
    ordering = ["-date_joined"]


@admin.register(Node)
class NodeAdmin(GISModelAdmin):
    list_display = ["name", "mesh_identity", "role", "latitude", "longitude", "is_active", "last_seen"]
    list_filter = ["role", "is_active", "firmware_version"]
    search_fields = ["name", "mesh_identity", "public_key", "description"]
    readonly_fields = ["first_seen", "last_seen", "latitude", "longitude"]
    fieldsets = [
        ("Identity", {"fields": ["mesh_identity", "public_key", "firmware_version", "role"]}),
        ("Information", {"fields": ["name", "description", "owner"]}),
        ("Location", {"fields": ["location", "latitude", "longitude", "altitude", "estimated_range"]}),
        ("Status", {"fields": ["is_active", "first_seen", "last_seen"]}),
    ]


@admin.register(RepeaterStats)
class RepeaterStatsAdmin(admin.ModelAdmin):
    list_display = ["node", "timestamp", "battery_voltage", "last_rssi", "last_snr", "n_packets_recv", "n_packets_sent"]
    list_filter = ["timestamp", "node"]
    search_fields = ["node__name", "node__mesh_identity"]
    readonly_fields = ["timestamp", "battery_voltage"]
    date_hierarchy = "timestamp"
    fieldsets = [
        ("Node", {"fields": ["node", "timestamp"]}),
        ("Power", {"fields": ["batt_milli_volts", "battery_voltage"]}),
        ("Signal Quality", {"fields": ["noise_floor", "last_rssi", "last_snr", "curr_tx_queue_len"]}),
        (
            "Packet Statistics",
            {
                "fields": [
                    "n_packets_recv",
                    "n_packets_sent",
                    "n_recv_flood",
                    "n_recv_direct",
                    "n_sent_flood",
                    "n_sent_direct",
                    "n_flood_dups",
                    "n_direct_dups",
                ],
                "classes": ["collapse"],
            },
        ),
        ("Time Metrics", {"fields": ["total_air_time_secs", "total_rx_air_time_secs", "total_up_time_secs"]}),
        ("Errors", {"fields": ["err_events"]}),
    ]


@admin.register(NeighbourInfo)
class NeighbourInfoAdmin(admin.ModelAdmin):
    list_display = ["node", "neighbour", "snr", "last_updated"]
    list_filter = ["last_updated", "node"]
    search_fields = ["node__name", "node__mesh_identity", "neighbour__name", "neighbour__mesh_identity"]
    readonly_fields = ["last_updated"]
    fieldsets = [
        ("Relationship", {"fields": ["node", "neighbour"]}),
        ("Timestamps", {"fields": ["advert_timestamp", "heard_timestamp", "last_updated"]}),
        ("Signal Quality", {"fields": ["snr"]}),
    ]


@admin.register(MappingSession)
class MappingSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "target_node", "start_time", "end_time", "is_active"]
    list_filter = ["start_time", "end_time", "user", "target_node"]
    search_fields = ["user__username", "target_node__name", "target_node__mesh_identity", "notes"]
    readonly_fields = ["start_time", "is_active", "duration"]
    date_hierarchy = "start_time"
    fieldsets = [
        ("Session Info", {"fields": ["user", "target_node", "notes"]}),
        ("Timing", {"fields": ["start_time", "end_time", "is_active", "duration"]}),
    ]


@admin.register(Trace)
class TraceAdmin(GISModelAdmin):
    list_display = [
        "session",
        "timestamp",
        "snr_to_target",
        "snr_from_target",
        "trace_success",
        "gps_accuracy",
    ]
    list_filter = ["timestamp", "session__target_node", "trace_success", "session"]
    search_fields = ["session__target_node__name", "session__target_node__mesh_identity", "session__user__username"]
    readonly_fields = ["timestamp", "target_node"]
    date_hierarchy = "timestamp"
    fieldsets = [
        ("Session", {"fields": ["session", "target_node", "timestamp"]}),
        ("Location", {"fields": ["location", "altitude", "gps_accuracy"]}),
        ("Signal Data", {"fields": ["snr_to_target", "snr_from_target", "trace_success"]}),
    ]
