import requests

from .models import Notification

# ============================================================
# OPENWEATHER API KEY
# Keep your key here as requested.
# ============================================================

OPENWEATHER_API_KEY = "PASTE_YOUR_OPENWEATHER_API_KEY_HERE"


# ============================================================
# CREATE NOTIFICATION
# ============================================================

def create_notification(
    user,
    title,
    message,
    notification_type,
    priority="normal",
    action="none",
):
    """
    Create notification while preventing duplicate unread entries.
    """

    if user is None:
        return None

    exists = Notification.objects.filter(
        user=user,
        title=title,
        message=message,
        is_read=False,
    ).exists()

    if exists:
        return None

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        priority=priority,
        action=action,
    )


# ============================================================
# WEATHER ALERT
# ============================================================

def check_weather_alert(user, latitude, longitude):
    """
    Fetch current weather and generate notifications.
    """

    if not latitude or not longitude:
        return

    url = (
        "https://api.openweathermap.org/data/2.5/weather"
        f"?lat={latitude}"
        f"&lon={longitude}"
        "&units=metric"
        f"&appid={OPENWEATHER_API_KEY}"
    )

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

    except requests.RequestException:
        return

    data = response.json()

    weather_main = (
        data.get("weather", [{}])[0]
        .get("main", "")
        .lower()
    )

    temp = data.get("main", {}).get("temp", 0)

    wind_speed = data.get("wind", {}).get("speed", 0)

    humidity = data.get("main", {}).get("humidity", 0)

    # Heavy Rain / Thunderstorm

    if weather_main in [
        "rain",
        "drizzle",
        "thunderstorm",
    ]:

        create_notification(
            user=user,
            title="🌧 Weather Alert",
            message="Aglay 24 ghanton mein barish ya thunderstorm ka imkan hai. Apni fasal aur machinery ko mehfooz rakhein.",
            notification_type="weather",
            priority="high",
            action="weather",
        )

    # Heat

    if temp >= 40:

        create_notification(
            user=user,
            title="🌡 High Temperature",
            message=f"Aaj darja hararat {temp}°C hai. Irrigation aur crop protection ka khayal rakhein.",
            notification_type="weather",
            priority="high",
            action="weather",
        )

    # Cold

    if temp <= 5:

        create_notification(
            user=user,
            title="❄ Cold Weather",
            message=f"Temperature sirf {temp}°C hai. Nazuk faslon ko sardi se bachayein.",
            notification_type="weather",
            priority="normal",
            action="weather",
        )

    # Strong Wind

    if wind_speed >= 12:

        create_notification(
            user=user,
            title="💨 Strong Wind",
            message="Tez hawaein chal rahi hain. Spray aur pesticide istemal karne se gurez karein.",
            notification_type="weather",
            priority="normal",
            action="weather",
        )

    # Low Humidity

    if humidity <= 25:

        create_notification(
            user=user,
            title="💧 Low Humidity",
            message="Humidity bohat kam hai. Crop water requirement check karein.",
            notification_type="weather",
            priority="normal",
            action="weather",
        )


# ============================================================
# SOIL MOISTURE
# ============================================================

def check_soil_moisture(user, moisture):

    if moisture is None:
        return

    if moisture < 30:

        create_notification(
            user=user,
            title="⚠ Soil Moisture Alert",
            message="Mitti mein nami bohat kam ho gayi hai. Irrigation ki zarurat hai.",
            notification_type="soil",
            priority="critical",
            action="iot",
        )

    elif moisture > 90:

        create_notification(
            user=user,
            title="💦 High Soil Moisture",
            message="Mitti mein pani bohat zyada hai. Water logging ka khatra ho sakta hai.",
            notification_type="soil",
            priority="high",
            action="iot",
        )

# ============================================================
# PROFILE COMPLETION
# ============================================================

def check_profile_completion(user):
    """
    Check whether the farmer profile is sufficiently complete.
    Matches your FarmerProfile model.
    """

    profile = getattr(user, "farmer_profile", None)

    if profile is None:
        return

    missing_fields = []

    if not profile.phone:
        missing_fields.append("Phone Number")

    if not profile.region:
        missing_fields.append("Region")

    if not profile.village:
        missing_fields.append("Village")

    if profile.land_acres is None:
        missing_fields.append("Land Size")

    if not profile.primary_crop:
        missing_fields.append("Primary Crop")

    if missing_fields:

        create_notification(
            user=user,
            title="👤 Complete Your Profile",
            message=(
                "Aap ki profile mukammal nahi hai. "
                "Phone, Region, Village, Land Size aur Primary Crop update karein "
                "taake AI behtar mashwaray de sake."
            ),
            notification_type="profile",
            priority="normal",
            action="profile",
        )


# ============================================================
# AI REPORT READY
# ============================================================

def send_ai_report_notification(user):

    create_notification(
        user=user,
        title="📋 AI Crop Report Ready",
        message="Aap ki AI crop report taiyar hai. Report section mein ja kar dekhein.",
        notification_type="ai_report",
        priority="normal",
        action="report",
    )


# ============================================================
# AI FOLLOW-UP
# ============================================================

def send_ai_followup_notification(
    user,
    crop_name=None,
):
    """
    Send a follow-up notification after AI consultation.
    """

    if crop_name:

        message = (
            f"Aap ne {crop_name} ke mutaliq AI se mashwara liya tha. "
            "Kya masla hal ho gaya? Zarurat ho to dobara AI se rabta karein."
        )

    else:

        message = (
            "Aap ke pichle AI mashware ke mutaliq follow-up tayyar hai. "
            "Agar zarurat ho to dobara AI se sawal karein."
        )

    create_notification(
        user=user,
        title="🌱 AI Follow-up",
        message=message,
        notification_type="followup",
        priority="normal",
        action="chat",
    )


# ============================================================
# SYSTEM NOTIFICATION
# ============================================================

def send_system_notification(
    user,
    title,
    message,
    priority="normal",
):

    create_notification(
        user=user,
        title=title,
        message=message,
        notification_type="system",
        priority=priority,
        action="none",
    )


# ============================================================
# LOGIN NOTIFICATION CHECKS
# ============================================================

def run_login_checks(
    user,
    latitude=None,
    longitude=None,
):
    """
    Run all notification checks after a successful login.

    Call this from your login API after authentication.
    """

    check_profile_completion(user)

    if latitude is not None and longitude is not None:
        check_weather_alert(
            user,
            latitude,
            longitude,
        )


# ============================================================
# IoT DATA CHECK
# ============================================================

def process_sensor_reading(
    user,
    moisture=None,
):
    """
    Call this whenever a new IoT reading is received.
    """

    if moisture is not None:
        check_soil_moisture(
            user,
            moisture,
        )


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "create_notification",
    "check_weather_alert",
    "check_soil_moisture",
    "check_profile_completion",
    "send_ai_report_notification",
    "send_ai_followup_notification",
    "send_system_notification",
    "run_login_checks",
    "process_sensor_reading",
]