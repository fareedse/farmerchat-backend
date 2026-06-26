import requests

from django.conf import settings

from .models import Notification


OPENWEATHER_API_KEY = "YOUR_OPENWEATHER_API_KEY"
OPENWEATHER_API_KEY = settings.OPENWEATHER_API_KEY

def create_notification(
    user,
    title,
    message,
    notification_type,
    priority="normal",
    action="none",
):
    """
    Prevent duplicate unread notifications.
    """

    exists = Notification.objects.filter(
        user=user,
        title=title,
        message=message,
        is_read=False,
    ).exists()

    if exists:
        return

    Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action=action,
    )


def check_weather_alert(user, latitude, longitude):
    """
    Check current weather.
    """

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}"
        f"&lon={longitude}"
        f"&units=metric"
        f"&appid={OPENWEATHER_API_KEY}"
    )

    response = requests.get(url, timeout=10)

    if response.status_code != 200:
        return

    weather = response.json()

    weather_main = weather["weather"][0]["main"].lower()

    temp = weather["main"]["temp"]

    if weather_main in ["rain", "thunderstorm"]:

        create_notification(
            user,
            "🌧️ Weather Warning",
            "Agly 24 ghanton mein tez barish ka imkan hai. Apni fasal ka khas khayal rakhin.",
            "weather",
            "high",
            "weather",
        )

    if temp >= 40:

        create_notification(
            user,
            "🌡️ High Temperature",
            f"Aaj temperature {temp}°C hai. Zarurat ke mutabiq irrigation karein.",
            "weather",
            "normal",
            "weather",
        )


def check_soil_moisture(user, moisture):

    if moisture < 30:

        create_notification(
            user,
            "⚠️ Soil Moisture Alert",
            "Mitti mein nami kam ho rahi hai! Baraye meharbani fasal ko pani dein.",
            "soil",
            "critical",
            "iot",
        )



def check_profile_completion(user):

    profile = getattr(user, "farmer_profile", None)

    if profile is None:
        return

    if not profile.phone or not profile.address:

        create_notification(
            user,
            "👤 Complete Profile",
            "Apni profile mukammal karein taake behtar mashwaray mil saken.",
            "profile",
            "normal",
            "profile",
        )

create_notification(
    user,
    "📋 AI Crop Report",
    "Aap ki fasal ki report taiyar hai. Click karke report dekhein.",
    "ai_report",
    "normal",
    "report",
)

create_notification(
    user,
    "🌱 AI Follow-up",
    "Aap ne mooli ki bimari ka pucha tha. Kya ab fasal ki surat-e-haal behtar hai?",
    "followup",
    "normal",
    "chat",
)