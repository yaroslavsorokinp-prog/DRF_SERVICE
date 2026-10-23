from rest_framework import serializers

from .models import Review, ReviewVote


class ReviewSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "location",
            "author",
            "rating",
            "comment",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "author",
            "created_at",
            "updated_at",
        ]

    def validate_location(self, value):
        if value.is_deleted:
            raise serializers.ValidationError(
                "Cannot create a review for a deleted location."
            )

        return value

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")

        return value

    def validate(self, attrs):
        request = self.context["request"]
        location = attrs.get(
            "location",
            self.instance.location if self.instance is not None else None,
        )

        # PATCH requests may omit location. Existing reviews should not
        # conflict with themselves during PUT/PATCH validation.
        if location is None:
            return attrs

        duplicate_reviews = Review.objects.filter(
            location=location,
            author=request.user,
        )
        if self.instance is not None:
            duplicate_reviews = duplicate_reviews.exclude(pk=self.instance.pk)

        if duplicate_reviews.exists():
            raise serializers.ValidationError(
                "You have already reviewed this location."
            )

        return attrs


class ReviewVoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewVote
        fields = [
            "id",
            "review",
            "vote",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
        ]


class ReviewVoteActionSerializer(serializers.Serializer):
    vote = serializers.ChoiceField(choices=ReviewVote.VoteType.choices)
