from rest_framework import serializers

from .models import Location


class LocationSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    rating = serializers.FloatField(read_only=True)
    reviews_count = serializers.IntegerField(read_only=True)
    popularity = serializers.SerializerMethodField()

    def get_popularity(self, obj):
        return getattr(obj, "popularity", None)

    class Meta:
        model = Location
        fields = [
            "id",
            "name",
            "description",
            "category",
            "category_name",
            "address",
            "latitude",
            "longitude",
            "author",
            "rating",
            "reviews_count",
            "created_at",
            "updated_at",
            "popularity",
        ]
        read_only_fields = [
            "id",
            "author",
            "category_name",
            "rating",
            "reviews_count",
            "created_at",
            "updated_at",
            "popularity",
        ]