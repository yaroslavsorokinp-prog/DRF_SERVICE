from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.categories.views import CategoryViewSet
from apps.locations.views import LocationViewSet


router = DefaultRouter()

router.register("categories", CategoryViewSet, basename="category")
router.register("locations", LocationViewSet, basename="location")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/", include("apps.reviews.urls")),
    path("api/auth/", include("apps.users.urls")),
    path("api/", include("apps.locations.urls")),
]