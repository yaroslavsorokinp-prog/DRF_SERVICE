from django.conf import settings
from django.db import models


class Review(models.Model):
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
    )

    rating = models.PositiveSmallIntegerField()
    comment = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "author"],
                name="unique_review_per_user_location",
            ),
        ]

    def __str__(self):
        return f"{self.author} - {self.location} ({self.rating})"


class ReviewVote(models.Model):
    class VoteType(models.TextChoices):
        LIKE = "like", "Like"
        DISLIKE = "dislike", "Dislike"

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="review_votes",
    )

    vote = models.CharField(
        max_length=10,
        choices=VoteType.choices,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["review", "user"],
                name="unique_vote_per_user_review",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.review_id} - {self.vote}"