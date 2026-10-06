from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.locations.models import Location


User = get_user_model()


class LocationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123",
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
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

    def test_locations_list_is_available_for_anonymous_user(self):
        response = self.client.get("/api/locations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_location_requires_authentication(self):
        response = self.client.post(
            "/api/locations/",
            {
                "name": "Новая локация",
                "description": "Описание",
                "category": self.category.id,
                "address": "Адрес",
                "latitude": 48.464700,
                "longitude": 35.046200,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_authenticated_user_can_create_location(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/locations/",
            {
                "name": "Новая локация",
                "description": "Описание",
                "category": self.category.id,
                "address": "Адрес",
                "latitude": 48.464700,
                "longitude": 35.046200,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["author"],
            self.user.username,
        )

    def test_owner_can_update_location(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/locations/{self.location.id}/",
            {
                "name": "Обновлённая локация",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.location.refresh_from_db()

        self.assertEqual(
            self.location.name,
            "Обновлённая локация",
        )

    def test_other_user_cannot_update_location(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.patch(
            f"/api/locations/{self.location.id}/",
            {
                "name": "Чужое изменение",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_delete_location_is_soft_delete(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            f"/api/locations/{self.location.id}/"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(
            Location.objects.filter(id=self.location.id).exists()
        )

        self.assertTrue(
            Location.all_objects.filter(
                id=self.location.id,
                is_deleted=True,
            ).exists()
        )

    def test_same_user_cannot_count_view_twice_within_hour(self):
        response = self.client.get(
            f"/api/locations/{self.location.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(
            f"/api/locations/{self.location.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)