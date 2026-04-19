from django.contrib import admin
from .models import (FarmerProfile, Expert, ChatSession, ChatMessage,
                     MarketRate, GovernmentScheme, IoTDevice, SensorReading,
                     WeatherAlert, ContentItem)

@admin.register(MarketRate)
class MarketRateAdmin(admin.ModelAdmin):
    list_display  = ('crop_name', 'mandi_name', 'region', 'price', 'price_change', 'status', 'date_recorded')
    list_filter   = ('status', 'region')
    search_fields = ('crop_name', 'mandi_name', 'region')
    list_editable = ('status',)

@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display  = ('title', 'category', 'target_region', 'status', 'beneficiaries', 'deadline')
    list_filter   = ('status', 'category')
    search_fields = ('title', 'target_region')
    list_editable = ('status',)

@admin.register(FarmerProfile)
class FarmerProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'region', 'primary_crop', 'language', 'is_verified', 'joined_at')
    list_filter   = ('region', 'language', 'is_verified')
    search_fields = ('user__username', 'user__first_name', 'region')

@admin.register(IoTDevice)
class IoTDeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'farm_name', 'location', 'device_type', 'is_active', 'last_ping')
    list_filter  = ('is_active', 'device_type')

@admin.register(SensorReading)
class SensorReadingAdmin(admin.ModelAdmin):
    list_display = ('device', 'moisture', 'temperature', 'humidity', 'timestamp')
    list_filter  = ('device',)

admin.site.register(Expert)
admin.site.register(ChatSession)
admin.site.register(ChatMessage)
admin.site.register(WeatherAlert)
admin.site.register(ContentItem)
