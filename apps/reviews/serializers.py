from rest_framework import serializers

from apps.locations.models import Location

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
            raise serializers.ValidationError("Cannot create a review for a deleted location.")

        return value

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")

        return value

    def validate(self, attrs):
        request = self.context["request"]
        location = attrs["location"]

        if Review.objects.filter(location=location, author=request.user).exists():
            raise serializers.ValidationError("You have already reviewed this location.")

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