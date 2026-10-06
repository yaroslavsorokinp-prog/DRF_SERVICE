from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ReviewViewSet, ReviewVoteView


router = DefaultRouter()

router.register("reviews", ReviewViewSet, basename="review")

urlpatterns = [
    path("reviews/<int:review_id>/vote/", ReviewVoteView.as_view(), name="review-vote"),
]

urlpatterns += router.urls