from django.urls import path

from apps.locations.views import LocationSubscriptionView


urlpatterns = [
    path("locations/<int:location_id>/subscribe/", LocationSubscriptionView.as_view(), name="location-subscribe"),
]