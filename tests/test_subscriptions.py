from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.locations.models import Location, LocationSubscription


User = get_user_model()


class LocationSubscriptionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
        )

        self.category = Category.objects.create(
            name="Парки",
            description="Парки города",
        )

        self.location = Location.objects.create(
            category=self.category,
            author=self.user,
            name="Тестовая локация",
            description="Описание",
            address="Тестовая улица, 10",
            latitude=48.464700,
            longitude=35.046200,
        )

    def test_authenticated_user_can_subscribe_to_location(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            f"/api/locations/{self.location.id}/subscribe/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            LocationSubscription.objects.filter(
                user=self.user,
                location=self.location,
            ).exists()
        )

    def test_user_cannot_subscribe_twice_to_same_location(self):
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(
            f"/api/locations/{self.location.id}/subscribe/",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            f"/api/locations/{self.location.id}/subscribe/",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            LocationSubscription.objects.filter(
                user=self.user,
                location=self.location,
            ).count(),
            1,
        )

    def test_authenticated_user_can_unsubscribe_from_location(self):
        LocationSubscription.objects.create(
            user=self.user,
            location=self.location,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            f"/api/locations/{self.location.id}/subscribe/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            LocationSubscription.objects.filter(
                user=self.user,
                location=self.location,
            ).exists()
        )

    def test_anonymous_user_cannot_subscribe_to_location(self):
        response = self.client.post(
            f"/api/locations/{self.location.id}/subscribe/",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )