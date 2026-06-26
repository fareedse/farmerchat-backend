from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from core.services import (
    check_weather_alert,
    check_profile_completion,
    check_soil_moisture,
)

User = get_user_model()


class Command(BaseCommand):
    help = "Generate farmer notifications"

    def handle(self, *args, **kwargs):

        users = User.objects.all()

        for user in users:

            try:
                profile = user.farmer_profile

                latitude = profile.latitude
                longitude = profile.longitude

                check_weather_alert(
                    user,
                    latitude,
                    longitude,
                )

            except Exception:
                pass

            try:
                latest = (
                    profile.sensorreadings
                    .order_by("-created_at")
                    .first()
                )

                if latest:
                    check_soil_moisture(
                        user,
                        latest.moisture,
                    )

            except Exception:
                pass

            try:
                check_profile_completion(user)

            except Exception:
                pass

        self.stdout.write(
            self.style.SUCCESS(
                "Notifications generated."
            )
        )