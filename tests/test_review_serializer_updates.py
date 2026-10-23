from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.categories.models import Category
from apps.locations.models import Location
from apps.reviews.models import Review

User = get_user_model()


class ReviewUpdateValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="review_owner",
            password="TestPassword123",
        )
        self.other_user = User.objects.create_user(
            username="other_user",
            password="TestPassword123",
        )
        self.category = Category.objects.create(
            name="Test category",
            description="Test category description",
        )
        self.location = Location.objects.create(
            category=self.category,
            author=self.user,
            name="First location",
            description="Description",
            address="First address",
            latitude=48.464700,
            longitude=35.046200,
        )
        self.review = Review.objects.create(
            location=self.location,
            author=self.user,
            rating=5,
            comment="Original review",
        )

    def test_author_can_patch_own_review_without_changing_location(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/reviews/{self.review.pk}/",
            {"rating": 4},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rating"], 4)

    def test_author_cannot_move_review_to_location_already_reviewed(self):
        second_location = Location.objects.create(
            category=self.category,
            author=self.other_user,
            name="Second location",
            description="Description",
            address="Second address",
            latitude=48.465000,
            longitude=35.047000,
        )
        Review.objects.create(
            location=second_location,
            author=self.user,
            rating=3,
            comment="Existing review for second location",
        )
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            f"/api/reviews/{self.review.pk}/",
            {"location": second_location.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
