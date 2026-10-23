from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.locations.models import Location
from apps.locations.services import (
    get_location_views_bulk,
    register_location_view,
)

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

        response = self.client.delete(f"/api/locations/{self.location.id}/")

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertFalse(Location.objects.filter(id=self.location.id).exists())

        self.assertTrue(
            Location.all_objects.filter(
                id=self.location.id,
                is_deleted=True,
            ).exists()
        )

    def test_same_user_cannot_count_view_twice_within_hour(self):
        response = self.client.get(f"/api/locations/{self.location.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/api/locations/{self.location.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RegisterLocationViewTests(TestCase):
    def setUp(self):
        self.request = MagicMock()
        self.request.user.is_authenticated = True
        self.request.user.id = 123

    @patch("apps.locations.services.get_redis_connection")
    def test_first_view_is_registered(self, mock_get_redis):
        redis = mock_get_redis.return_value
        redis.set.return_value = True

        result = register_location_view(1, self.request)

        self.assertTrue(result)
        redis.set.assert_called_once_with(
            "location:1:viewed:user:123",
            "1",
            nx=True,
            ex=3600,
        )
        redis.zadd.assert_called_once()
        redis.expire.assert_called_once()

    @patch("apps.locations.services.get_redis_connection")
    def test_repeated_view_is_not_registered(self, mock_get_redis):
        redis = mock_get_redis.return_value
        redis.set.return_value = None

        result = register_location_view(1, self.request)

        self.assertFalse(result)
        redis.zadd.assert_not_called()
        redis.expire.assert_not_called()


class LocationViewsBulkTests(TestCase):
    @patch("apps.locations.services.get_redis_connection")
    def test_bulk_views_uses_pipeline_and_maps_results(self, mock_get_redis):
        redis = mock_get_redis.return_value
        pipeline = redis.pipeline.return_value
        pipeline.execute.return_value = [2, 3, 4, 5]

        result = get_location_views_bulk([10, 20])

        redis.pipeline.assert_called_once_with(transaction=False)

        calls = pipeline.zremrangebyscore.call_args_list

        self.assertEqual(len(calls), 2)
        self.assertEqual(
            [call.args[0] for call in calls],
            ["location:10:views", "location:20:views"],
        )
        self.assertTrue(all(call.args[1] == 0 for call in calls))
        self.assertEqual(
            [call.args[0] for call in pipeline.zcard.call_args_list],
            ["location:10:views", "location:20:views"],
        )

        pipeline.zcard.assert_any_call("location:10:views")
        pipeline.zcard.assert_any_call("location:20:views")
        pipeline.execute.assert_called_once_with()

        self.assertEqual(result, {10: 3, 20: 5})

    @patch("apps.locations.services.get_redis_connection")
    def test_empty_location_ids_do_not_connect_to_redis(self, mock_get_redis):
        result = get_location_views_bulk([])

        self.assertEqual(result, {})
        mock_get_redis.assert_not_called()


class LocationViewsPaginationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pagination_user",
            password="TestPassword123",
        )
        self.category = Category.objects.create(
            name="Тестовая категория",
            description="Для тестирования пагинации",
        )

        self.locations = [
            Location.objects.create(
                category=self.category,
                author=self.user,
                name=f"Локация {index}",
                description="Описание",
                address=f"Адрес {index}",
                latitude=48.464700,
                longitude=35.046200,
            )
            for index in range(12)
        ]

    @patch("apps.locations.views.get_location_views_bulk")
    @patch("apps.locations.views.cache.set")
    @patch("apps.locations.views.cache.get", return_value=None)
    def test_regular_list_counts_views_only_for_current_page(
        self,
        mock_cache_get,
        mock_cache_set,
        mock_get_views,
    ):
        mock_get_views.side_effect = lambda ids: {location_id: 0 for location_id in ids}

        response = self.client.get("/api/locations/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        page_ids = [item["id"] for item in response.data["results"]]

        self.assertEqual(len(page_ids), 10)
        mock_get_views.assert_called_once_with(page_ids)

    @patch("apps.locations.views.get_location_views_bulk")
    @patch("apps.locations.views.cache.set")
    @patch("apps.locations.views.cache.get", return_value=None)
    def test_popularity_sort_calculates_all_locations_before_pagination(
        self,
        mock_cache_get,
        mock_cache_set,
        mock_get_views,
    ):
        all_ids = [location.id for location in self.locations]
        mock_get_views.side_effect = lambda ids: {
            location_id: location_id for location_id in ids
        }

        response = self.client.get("/api/locations/?ordering=-popularity")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        mock_get_views.assert_called_once()
        requested_ids = mock_get_views.call_args.args[0]

        self.assertEqual(set(requested_ids), set(all_ids))

        page_ids = [item["id"] for item in response.data["results"]]

        self.assertEqual(len(page_ids), 10)
        self.assertEqual(page_ids, sorted(all_ids, reverse=True)[:10])
