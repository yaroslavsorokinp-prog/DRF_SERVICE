from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.locations.models import Location
from apps.reviews.models import Review


User = get_user_model()


class ReviewAPITests(APITestCase):
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

        self.review = Review.objects.create(
            location=self.location,
            author=self.user,
            rating=5,
            comment="Отличное место!",
        )

    def test_authenticated_user_can_create_review(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            "/api/reviews/",
            {
                "location": self.location.id,
                "rating": 5,
                "comment": "Отличное место!",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            Review.objects.filter(
                location=self.location,
                author=self.other_user,
            ).exists()
        )

    def test_user_cannot_create_duplicate_review(self):
        Review.objects.create(
            location=self.location,
            author=self.other_user,
            rating=5,
            comment="Первый отзыв",
        )

        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            "/api/reviews/",
            {
                "location": self.location.id,
                "rating": 4,
                "comment": "Второй отзыв",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_rating_must_be_between_1_and_5(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            "/api/reviews/",
            {
                "location": self.location.id,
                "rating": 6,
                "comment": "Неверный рейтинг",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_anonymous_user_cannot_create_review(self):
        response = self.client.post(
            "/api/reviews/",
            {
                "location": self.location.id,
                "rating": 5,
                "comment": "Анонимный отзыв",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


    def test_authenticated_user_can_vote_for_review(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            f"/api/reviews/{self.review.id}/vote/",
            {"vote": "like"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


    def test_user_cannot_vote_twice_for_same_review(self):
        self.client.force_authenticate(user=self.other_user)

        first_response = self.client.post(
            f"/api/reviews/{self.review.id}/vote/",
            {"vote": "like"},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        second_response = self.client.post(
            f"/api/reviews/{self.review.id}/vote/",
            {"vote": "dislike"},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )