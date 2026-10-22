import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError, transaction

from rest_framework import serializers, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations.models import LocationSubscription
from apps.locations.services import invalidate_location_cache

from .models import Review, ReviewVote
from .permissions import IsReviewAuthorOrAdmin
from .serializers import (
    ReviewSerializer,
    ReviewVoteActionSerializer,
    ReviewVoteSerializer,
)


logger = logging.getLogger(__name__)


def send_review_notifications(review):
    location = review.location

    recipients = set()

    if location.author.email:
        recipients.add(location.author.email)

    subscriber_emails = LocationSubscription.objects.filter(
        location=location,
        user__email__isnull=False,
    ).exclude(
        user__email="",
    ).values_list(
        "user__email",
        flat=True,
    )

    recipients.update(subscriber_emails)

    for email in recipients:
        send_mail(
            subject="Новый отзыв на вашу локацию",
            message=(
                f'На локацию "{location.name}" оставили новый отзыв.\n\n'
                f"Оценка: {review.rating}/5\n"
                f"Комментарий: {review.comment}\n"
                f"Автор: {review.author}\n"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("location", "author").all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsReviewAuthorOrAdmin]

    def perform_create(self, serializer):
        try:
            with transaction.atomic():
                review = serializer.save(author=self.request.user)
        except IntegrityError:
            # The database constraint is the final guard against two
            # simultaneous requests creating a review for the same location.
            duplicate_exists = Review.objects.filter(
                location=serializer.validated_data["location"],
                author=self.request.user,
            ).exists()
            if duplicate_exists:
                raise serializers.ValidationError(
                    {"detail": "You have already reviewed this location."}
                )
            raise

        invalidate_location_cache()
        send_review_notifications(review)


class ReviewVoteView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, review_id):
        review = Review.objects.select_for_update().filter(pk=review_id).first()
        if review is None:
            return Response(
                {"detail": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        input_serializer = ReviewVoteActionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        vote_type = input_serializer.validated_data["vote"]

        vote = ReviewVote.objects.filter(
            review=review,
            user=request.user,
        ).first()

        if vote is not None:
            if vote.vote == vote_type:
                vote.delete()
                return Response(
                    {"detail": "Vote removed."},
                    status=status.HTTP_200_OK,
                )

            vote.vote = vote_type
            vote.save(update_fields=["vote"])
            return Response(
                ReviewVoteSerializer(vote).data,
                status=status.HTTP_200_OK,
            )

        vote = ReviewVote.objects.create(
            review=review,
            user=request.user,
            vote=vote_type,
        )
        return Response(
            ReviewVoteSerializer(vote).data,
            status=status.HTTP_201_CREATED,
        )
