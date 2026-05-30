"""
FarmerChat Admin — Database Models
====================================
Complete schema for all modules:
  1. FarmerProfile    — registered farmers
  2. Expert           — agricultural experts
  3. ChatSession      — farmer ↔ AI conversations
  4. ChatMessage      — individual messages
  5. MarketRate       — daily crop prices per mandi
  6. GovernmentScheme — subsidy & aid programs
  7. IoTDevice        — registered sensor nodes
  8. SensorReading    — live sensor data
  9. WeatherAlert     — system-wide alerts
 10. ContentItem      — announcements / articles
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ─────────────────────────────────────────────────────────────────────────────
# 1. FARMER PROFILE
# ─────────────────────────────────────────────────────────────────────────────

class FarmerProfile(models.Model):
    LANG_CHOICES = [
        ("ur", "Urdu"),
        ("pa", "Punjabi"),
        ("en", "English"),
        ("sd", "Sindhi"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="farmer_profile"
    )
    phone = models.CharField(max_length=20, blank=True)
    region = models.CharField(max_length=100, blank=True, db_index=True)
    village = models.CharField(max_length=100, blank=True)
    land_acres = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    primary_crop = models.CharField(max_length=100, blank=True, db_index=True)
    language = models.CharField(max_length=5, choices=LANG_CHOICES, default="ur")
    is_verified = models.BooleanField(default=False)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-joined_at"]
        verbose_name = "Farmer Profile"
        verbose_name_plural = "Farmer Profiles"

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} — {self.region or 'Unknown Region'}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXPERT
# ─────────────────────────────────────────────────────────────────────────────

class Expert(models.Model):
    STATUS = [
        ("available", "Available"),
        ("busy", "Busy"),
        ("offline", "Offline"),
    ]

    SPECIALIZATION = [
        ("crop_disease", "Crop Disease"),
        ("irrigation", "Irrigation"),
        ("fertilizer", "Fertilizer"),
        ("market", "Market Prices"),
        ("weather", "Weather"),
        ("general", "General"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="expert_profile"
    )
    specialization = models.CharField(
        max_length=50,
        choices=SPECIALIZATION,
        default="general",
        db_index=True
    )
    status = models.CharField(max_length=20, choices=STATUS, default="offline", db_index=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=5.0)
    total_chats = models.PositiveIntegerField(default=0)
    bio = models.TextField(blank=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-rating", "-joined_at"]
        verbose_name = "Expert"
        verbose_name_plural = "Experts"

    def __str__(self):
        name = self.user.get_full_name() or self.user.username
        return f"{name} — {self.get_specialization_display()}"


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHAT SESSION
# ─────────────────────────────────────────────────────────────────────────────

class ChatSession(models.Model):
    STATUS = [
        ("active", "Active"),
        ("closed", "Closed"),
        ("pending", "Pending"),
    ]

    TYPE = [
        ("ai", "AI Chat"),
        ("expert", "Expert Chat"),
    ]

    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="chat_sessions",
        null=True,
        blank=True,
        help_text="Can be empty for public/mobile guest chatbot messages."
    )
    expert = models.ForeignKey(
        Expert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    session_type = models.CharField(max_length=10, choices=TYPE, default="ai")
    topic = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="active", db_index=True)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Chat Session"
        verbose_name_plural = "Chat Sessions"

    def message_count(self):
        return self.messages.count()

    def __str__(self):
        farmer_name = self.farmer.username if self.farmer else "Guest Farmer"
        return f"Session #{self.pk} — {farmer_name}"


# ─────────────────────────────────────────────────────────────────────────────
# 4. CHAT MESSAGE
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessage(models.Model):
    ROLE = [
        ("user", "Farmer"),
        ("assistant", "AI"),
        ("expert", "Expert"),
        ("system", "System"),
    ]

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    role = models.CharField(max_length=15, choices=ROLE, default="user", db_index=True)
    content = models.TextField()
    language = models.CharField(max_length=5, default="ur", db_index=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["timestamp"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


# ─────────────────────────────────────────────────────────────────────────────
# 5. MARKET RATE
# ─────────────────────────────────────────────────────────────────────────────

class MarketRate(models.Model):
    STATUS = [
        ("published", "Published"),
        ("pending", "Pending"),
        ("draft", "Draft"),
    ]

    UNIT = [
        ("40kg", "PKR / 40kg"),
        ("mound", "PKR / Mound"),
        ("kg", "PKR / kg"),
        ("ton", "PKR / Ton"),
    ]

    crop_name = models.CharField(max_length=100, db_index=True)
    crop_name_ur = models.CharField(max_length=100, blank=True, help_text="Urdu name e.g. گندم")
    mandi_name = models.CharField(max_length=150, db_index=True)
    region = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, choices=UNIT, default="40kg")
    price_change = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="% change from yesterday. Positive = up, negative = down."
    )
    status = models.CharField(max_length=15, choices=STATUS, default="draft", db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_recorded = models.DateField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_recorded", "-updated_at"]
        verbose_name = "Market Rate"
        verbose_name_plural = "Market Rates"
        indexes = [
            models.Index(fields=["crop_name", "region"]),
            models.Index(fields=["mandi_name", "date_recorded"]),
            models.Index(fields=["status", "date_recorded"]),
        ]

    def __str__(self):
        return f"{self.crop_name} — {self.mandi_name} — PKR {self.price}"

    @property
    def change_direction(self):
        if self.price_change > 0:
            return "up"
        if self.price_change < 0:
            return "down"
        return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# 6. GOVERNMENT SCHEME
# ─────────────────────────────────────────────────────────────────────────────

class GovernmentScheme(models.Model):
    STATUS = [
        ("active", "Active"),
        ("review", "Under Review"),
        ("draft", "Draft"),
        ("expired", "Expired"),
    ]

    CATEGORY = [
        ("subsidy", "Financial Subsidy"),
        ("equipment", "Equipment / Machinery"),
        ("water", "Water Management"),
        ("seeds", "Seeds & Fertilizer"),
        ("solar", "Solar / Energy"),
        ("organic", "Organic Farming"),
        ("insurance", "Crop Insurance"),
        ("training", "Training & Education"),
    ]

    title = models.CharField(max_length=200, db_index=True)
    title_ur = models.CharField(max_length=200, blank=True, help_text="Urdu title")
    description = models.TextField()

    eligibility = models.TextField(
        blank=True,
        help_text="Who can apply for this scheme?"
    )
    benefits = models.TextField(
        blank=True,
        help_text="Main benefits of the scheme."
    )
    application_process = models.TextField(
        blank=True,
        help_text="How farmers can apply."
    )
    required_documents = models.TextField(
        blank=True,
        help_text="CNIC, land record, application form, etc."
    )
    official_link = models.URLField(blank=True)

    category = models.CharField(max_length=20, choices=CATEGORY, default="subsidy", db_index=True)
    target_region = models.CharField(max_length=200, default="All Regions", db_index=True)
    beneficiaries = models.PositiveIntegerField(default=0, help_text="Number of registered beneficiaries")
    budget_pkr = models.BigIntegerField(null=True, blank=True, help_text="Total budget in PKR")
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=STATUS, default="draft", db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Government Scheme"
        verbose_name_plural = "Government Schemes"
        indexes = [
            models.Index(fields=["status", "category"]),
            models.Index(fields=["target_region", "status"]),
            models.Index(fields=["deadline"]),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"


# ─────────────────────────────────────────────────────────────────────────────
# 7. IoT DEVICE
# ─────────────────────────────────────────────────────────────────────────────

class IoTDevice(models.Model):
    DEVICE_TYPE = [
        ("full", "Full Kit (Soil + DHT22)"),
        ("soil", "Soil Only"),
        ("weather", "Weather Station"),
    ]

    device_id = models.CharField(max_length=50, unique=True, db_index=True)
    farm_name = models.CharField(max_length=150)
    farmer = models.ForeignKey(
        FarmerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    location = models.CharField(max_length=200)
    device_type = models.CharField(max_length=15, choices=DEVICE_TYPE, default="full")
    is_active = models.BooleanField(default=True)
    last_ping = models.DateTimeField(null=True, blank=True, db_index=True)
    registered = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered"]
        verbose_name = "IoT Device"
        verbose_name_plural = "IoT Devices"

    def __str__(self):
        return f"{self.device_id} — {self.farm_name}"

    @property
    def is_online(self):
        if not self.last_ping:
            return False
        delta = timezone.now() - self.last_ping
        return delta.total_seconds() < 120


# ─────────────────────────────────────────────────────────────────────────────
# 8. SENSOR READING
# ─────────────────────────────────────────────────────────────────────────────

class SensorReading(models.Model):
    device = models.ForeignKey(
        IoTDevice,
        on_delete=models.CASCADE,
        related_name="readings"
    )
    moisture = models.FloatField(null=True, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    humidity = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Sensor Reading"
        verbose_name_plural = "Sensor Readings"
        indexes = [
            models.Index(fields=["device", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.device.device_id} @ {self.timestamp:%Y-%m-%d %H:%M:%S}"


# ─────────────────────────────────────────────────────────────────────────────
# 9. WEATHER ALERT
# ─────────────────────────────────────────────────────────────────────────────

class WeatherAlert(models.Model):
    SEVERITY = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    title = models.CharField(max_length=200)
    message = models.TextField()
    region = models.CharField(max_length=200, default="All Regions", db_index=True)
    severity = models.CharField(max_length=15, choices=SEVERITY, default="low", db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    issued_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]
        verbose_name = "Weather Alert"
        verbose_name_plural = "Weather Alerts"

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


# ─────────────────────────────────────────────────────────────────────────────
# 10. CONTENT ITEM
# ─────────────────────────────────────────────────────────────────────────────

class ContentItem(models.Model):
    TYPE = [
        ("article", "Article"),
        ("announcement", "Announcement"),
        ("tip", "Farming Tip"),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    item_type = models.CharField(max_length=20, choices=TYPE, default="article", db_index=True)
    region = models.CharField(max_length=200, default="All Regions", db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Content Item"
        verbose_name_plural = "Content Items"

    def __str__(self):
        return f"[{self.item_type}] {self.title}"