from django.contrib import admin
from .models import (
    FarmerProfile,
    Expert,
    ChatSession,
    ChatMessage,
    MarketRate,
    GovernmentScheme,
    IoTDevice,
    SensorReading,
    WeatherAlert,
    ContentItem,
)


# ─────────────────────────────────────────────────────────────────────────────
# MARKET RATES
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(MarketRate)
class MarketRateAdmin(admin.ModelAdmin):
    list_display = (
        "crop_name",
        "crop_name_ur",
        "mandi_name",
        "region",
        "price",
        "unit",
        "price_change",
        "change_direction",
        "status",
        "date_recorded",
        "created_by",
        "updated_at",
    )
    list_filter = (
        "status",
        "unit",
        "region",
        "date_recorded",
    )
    search_fields = (
        "crop_name",
        "crop_name_ur",
        "mandi_name",
        "region",
    )
    list_editable = (
        "status",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "-date_recorded",
        "-updated_at",
    )
    date_hierarchy = "date_recorded"

    fieldsets = (
        ("Crop & Market Information", {
            "fields": (
                "crop_name",
                "crop_name_ur",
                "mandi_name",
                "region",
            )
        }),
        ("Price Details", {
            "fields": (
                "price",
                "unit",
                "price_change",
                "status",
                "date_recorded",
            )
        }),
        ("System Information", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GOVERNMENT SCHEMES
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "target_region",
        "status",
        "beneficiaries",
        "budget_pkr",
        "deadline",
        "created_by",
        "updated_at",
    )
    list_filter = (
        "status",
        "category",
        "target_region",
        "deadline",
    )
    search_fields = (
        "title",
        "title_ur",
        "description",
        "target_region",
        "eligibility",
        "benefits",
    )
    list_editable = (
        "status",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    ordering = (
        "-created_at",
    )
    date_hierarchy = "created_at"

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "title",
                "title_ur",
                "description",
                "category",
                "target_region",
                "status",
            )
        }),
        ("Scheme Details", {
            "fields": (
                "eligibility",
                "benefits",
                "application_process",
                "required_documents",
                "official_link",
            )
        }),
        ("Numbers & Dates", {
            "fields": (
                "beneficiaries",
                "budget_pkr",
                "deadline",
            )
        }),
        ("System Information", {
            "fields": (
                "created_by",
                "created_at",
                "updated_at",
            )
        }),
    )


# ─────────────────────────────────────────────────────────────────────────────
# FARMERS
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "phone",
        "region",
        "village",
        "primary_crop",
        "land_acres",
        "language",
        "is_verified",
        "joined_at",
    )
    list_filter = (
        "region",
        "language",
        "is_verified",
        "primary_crop",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "phone",
        "region",
        "village",
        "primary_crop",
    )
    list_editable = (
        "is_verified",
    )
    readonly_fields = (
        "joined_at",
    )
    ordering = (
        "-joined_at",
    )
    date_hierarchy = "joined_at"


# ─────────────────────────────────────────────────────────────────────────────
# EXPERTS
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Expert)
class ExpertAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "specialization",
        "status",
        "rating",
        "total_chats",
        "joined_at",
    )
    list_filter = (
        "specialization",
        "status",
    )
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "bio",
    )
    list_editable = (
        "status",
    )
    readonly_fields = (
        "joined_at",
    )
    ordering = (
        "-rating",
        "-joined_at",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────────────────

class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = (
        "role",
        "content",
        "language",
        "timestamp",
    )
    fields = (
        "role",
        "content",
        "language",
        "timestamp",
    )
    can_delete = False


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "farmer",
        "session_type",
        "topic",
        "status",
        "message_count",
        "started_at",
        "ended_at",
    )
    list_filter = (
        "session_type",
        "status",
        "started_at",
    )
    search_fields = (
        "farmer__username",
        "farmer__first_name",
        "farmer__last_name",
        "topic",
    )
    readonly_fields = (
        "started_at",
    )
    ordering = (
        "-started_at",
    )
    date_hierarchy = "started_at"
    inlines = [
        ChatMessageInline,
    ]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "role",
        "short_content",
        "language",
        "timestamp",
    )
    list_filter = (
        "role",
        "language",
        "timestamp",
    )
    search_fields = (
        "content",
        "session__topic",
    )
    readonly_fields = (
        "timestamp",
    )
    ordering = (
        "-timestamp",
    )
    date_hierarchy = "timestamp"

    def short_content(self, obj):
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content

    short_content.short_description = "Message"


# ─────────────────────────────────────────────────────────────────────────────
# IoT DEVICES
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(IoTDevice)
class IoTDeviceAdmin(admin.ModelAdmin):
    list_display = (
        "device_id",
        "farm_name",
        "farmer",
        "location",
        "device_type",
        "is_active",
        "is_online",
        "last_ping",
        "registered",
    )
    list_filter = (
        "is_active",
        "device_type",
        "registered",
    )
    search_fields = (
        "device_id",
        "farm_name",
        "location",
        "farmer__user__username",
    )
    readonly_fields = (
        "last_ping",
        "registered",
    )
    ordering = (
        "-registered",
    )


@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = (
        "device",
        "moisture",
        "temperature",
        "humidity",
        "timestamp",
    )
    list_filter = (
        "device",
        "timestamp",
    )
    search_fields = (
        "device__device_id",
        "device__farm_name",
        "device__location",
    )
    readonly_fields = (
        "timestamp",
    )
    ordering = (
        "-timestamp",
    )
    date_hierarchy = "timestamp"


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER ALERTS
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(WeatherAlert)
class WeatherAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "region",
        "severity",
        "is_active",
        "issued_at",
        "expires_at",
    )
    list_filter = (
        "severity",
        "is_active",
        "region",
        "issued_at",
    )
    search_fields = (
        "title",
        "message",
        "region",
    )
    list_editable = (
        "is_active",
    )
    readonly_fields = (
        "issued_at",
    )
    ordering = (
        "-issued_at",
    )


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "item_type",
        "region",
        "is_published",
        "created_by",
        "created_at",
    )
    list_filter = (
        "item_type",
        "region",
        "is_published",
        "created_at",
    )
    search_fields = (
        "title",
        "content",
        "region",
    )
    list_editable = (
        "is_published",
    )
    readonly_fields = (
        "created_at",
    )
    ordering = (
        "-created_at",
    )


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN SITE BRANDING
# ─────────────────────────────────────────────────────────────────────────────

admin.site.site_header = "FarmerChat Administration"
admin.site.site_title = "FarmerChat Admin"
admin.site.index_title = "FarmerChat Control Panel"