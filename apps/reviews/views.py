from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.locations.services import invalidate_location_cache
from apps.locations.models import LocationSubscription

from .models import Review, ReviewVote
from .permissions import IsReviewAuthorOrAdmin
from .serializers import ReviewSerializer, ReviewVoteSerializer

from django.core.mail import send_mail
from django.conf import settings


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
        review = serializer.save(author=self.request.user)
        invalidate_location_cache()
        send_review_notifications(review)


class ReviewVoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, review_id):
        if not Review.objects.filter(id=review_id).exists():
            return Response({"detail": "Review not found."}, status=status.HTTP_404_NOT_FOUND)

        if ReviewVote.objects.filter(review_id=review_id, user=request.user).exists():
            return Response({"detail": "You have already voted for this review."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewVoteSerializer(
            data={
                "review": review_id,
                "vote": request.data.get("vote"),
            }
        )

        serializer.is_valid(raise_exception=True)

        vote = serializer.save(user=request.user)

        return Response(ReviewVoteSerializer(vote).data, status=status.HTTP_201_CREATED)