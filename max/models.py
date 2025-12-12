from django.contrib.auth.models import AbstractUser
from django.contrib.gis.db import models as gis_models
from django.db import models
from django.urls import reverse


class User(AbstractUser):
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.username


class Role(models.IntegerChoices):
    REPEATER = 0, "Repeater"
    CLIENT = 1, "Client"


class Node(models.Model):
    """
    Represents a MeshCore node device in the mesh network.
    Can be a repeater, client, or other node type.
    Based on the MeshCore firmware v1.9.1 implementation.
    """

    # Identity and metadata
    mesh_identity = models.CharField(max_length=64, unique=True, help_text="Unique mesh network identity hash")
    public_key = models.TextField(unique=True, db_index=True, help_text="Cryptographic public key for the node")
    firmware_version = models.CharField(max_length=32, default="v1.9.1")
    role = models.IntegerField(choices=Role.choices, default=Role.REPEATER)

    # Location and deployment info
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    altitude = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altitude in meters",
    )
    estimated_range = models.PositiveIntegerField(
        default=1000,
        help_text="Estimated coverage range in meters (used for map visualization)",
    )

    # Administrative fields
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="nodes", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Node"
        verbose_name_plural = "Nodes"

    def __str__(self):
        return self.name or self.mesh_identity

    def get_absolute_url(self):
        return reverse("node_detail", kwargs={"node_id": self.id})

    @property
    def latitude(self):
        return self.location.y if self.location else None

    @property
    def longitude(self):
        return self.location.x if self.location else None


class RepeaterStats(models.Model):
    """
    Telemetry data from MeshCore repeaters.
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="telemetry_readings")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Power metrics
    batt_milli_volts = models.PositiveIntegerField(help_text="Battery voltage in millivolts")

    # Queue and signal metrics
    curr_tx_queue_len = models.PositiveIntegerField(help_text="Current transmit queue length")
    noise_floor = models.SmallIntegerField(help_text="Noise floor in dBm")
    last_rssi = models.SmallIntegerField(help_text="Last RSSI (Received Signal Strength Indicator) in dBm")
    last_snr = models.SmallIntegerField(help_text="Last SNR (Signal-to-Noise Ratio) in dB")

    # Packet statistics
    n_packets_recv = models.PositiveBigIntegerField(help_text="Total packets received")
    n_packets_sent = models.PositiveBigIntegerField(help_text="Total packets sent")
    n_recv_flood = models.PositiveBigIntegerField(help_text="Flood packets received")
    n_recv_direct = models.PositiveBigIntegerField(help_text="Direct packets received")
    n_sent_flood = models.PositiveBigIntegerField(help_text="Flood packets sent")
    n_sent_direct = models.PositiveBigIntegerField(help_text="Direct packets sent")
    n_flood_dups = models.PositiveIntegerField(help_text="Duplicate flood packets")
    n_direct_dups = models.PositiveIntegerField(help_text="Duplicate direct packets")

    # Time metrics
    total_air_time_secs = models.PositiveBigIntegerField(help_text="Total air time in seconds (TX)")
    total_rx_air_time_secs = models.PositiveBigIntegerField(help_text="Total air time in seconds (RX)")
    total_up_time_secs = models.PositiveBigIntegerField(help_text="Total uptime in seconds")

    # Error tracking
    err_events = models.PositiveIntegerField(help_text="Number of error events")

    class Meta:
        verbose_name = "Node Telemetry"
        verbose_name_plural = "Node Telemetry"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.node} - {self.timestamp}"

    @property
    def battery_voltage(self):
        """Return battery voltage in volts."""
        return self.batt_milli_volts / 1000.0


class NeighbourInfo(models.Model):
    """
    Represents a neighbouring node heard by a repeater.
    """

    node = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="neighbours")
    neighbour = models.ForeignKey(Node, on_delete=models.CASCADE, related_name="heard_by")
    advert_timestamp = models.PositiveBigIntegerField(help_text="Advertisement timestamp from firmware")
    heard_timestamp = models.PositiveBigIntegerField(help_text="Last heard timestamp from firmware")
    last_updated = models.DateTimeField(auto_now=True)
    snr = models.SmallIntegerField(help_text="Signal-to-Noise Ratio (multiplied by 4 in firmware)")

    class Meta:
        unique_together = ["node", "neighbour"]

    def __str__(self):
        return f"{self.neighbour} (neighbour of {self.node})"


class MappingSession(models.Model):
    """
    Represents an explicit mapping session where a user walks around collecting signal data.
    Sessions must be explicitly started and ended.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    target_node = models.ForeignKey(Node, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True, db_index=True)
    end_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text="Description of the mapping session")

    class Meta:
        verbose_name = "Mapping Session"
        verbose_name_plural = "Mapping Sessions"
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["user", "-start_time"]),
            models.Index(fields=["target_node", "-start_time"]),
        ]

    def __str__(self):
        status = "active" if self.end_time is None else "completed"
        return f"{self.user} mapping {self.target_node} ({status}) - {self.start_time}"

    @property
    def is_active(self):
        """Returns True if the session is still active (not ended)."""
        return self.end_time is None

    @property
    def duration(self):
        """Returns the duration of the session if completed, None otherwise."""
        if self.end_time:
            return self.end_time - self.start_time
        return None


class Trace(models.Model):
    """
    Stores individual signal trace measurements collected during a mapping session.
    Used for generating signal coverage heatmaps.
    """

    # Link to mapping session
    session = models.ForeignKey(MappingSession, on_delete=models.CASCADE)

    # Location (GeoDjango PointField - lon, lat order)
    location = gis_models.PointField(srid=4326, help_text="GPS coordinates (lon, lat)")
    altitude = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Altitude in meters (from browser geolocation, may be null)",
    )
    gps_accuracy = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="GPS horizontal accuracy in meters (from browser)",
    )

    # Signal data
    snr_to_target = models.FloatField(default=0.0, help_text="SNR at target node (our signal reaching the repeater) in dB")
    snr_from_target = models.FloatField(default=0.0, help_text="SNR at our device (repeater's signal reaching us) in dB")
    trace_success = models.BooleanField(default=False, help_text="Whether the trace command succeeded")

    # Collection metadata
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Trace"
        verbose_name_plural = "Traces"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["session", "-timestamp"]),
        ]

    def __str__(self):
        return f"Trace @ {self.location} - SNR: {self.snr_to_target}/{self.snr_from_target}dB ({self.timestamp})"

    @property
    def target_node(self):
        """Convenience property to access the target node through the session."""
        return self.session.target_node
