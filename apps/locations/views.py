from django.db.models import Avg, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.core.cache import cache

from .export import export_locations_csv
from rest_framework.decorators import action
from .filters import LocationFilter
from .models import Location
from .permissions import IsOwnerOrAdmin
from .serializers import LocationSerializer
from .services import (
    calculate_location_popularity,
    get_location_views_last_7_days,
    register_location_view,
    invalidate_location_cache,
)


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.select_related("category", "author").annotate(
        rating=Avg("reviews__rating"),
        reviews_count=Count("reviews"),
    )

    serializer_class = LocationSerializer

    filterset_class = LocationFilter

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]

    filterset_fields = ["category", "author"]

    search_fields = ["name", "description"]

    ordering_fields = ["created_at", "rating"]

    ordering = ["-created_at"]

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [AllowAny()]

        if self.action == "create":
            return [IsAuthenticated()]

        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsOwnerOrAdmin()]

        return super().get_permissions()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        register_location_view(location_id=instance.id, request=request)

        views_last_7_days = get_location_views_last_7_days(instance.id)

        popularity = calculate_location_popularity(
            rating=instance.rating,
            reviews_count=instance.reviews_count,
            views_last_7_days=views_last_7_days,
        )

        instance.popularity = popularity

        serializer = self.get_serializer(instance, context={"popularity": popularity})

        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        cache_key = f"locations:list:{request.get_full_path()}"

        cached_data = cache.get(cache_key)

        if cached_data is not None:
            return Response(cached_data)

        ordering = request.query_params.get("ordering")

        if ordering in ["popularity", "-popularity"]:
            queryset = self.get_queryset()

            queryset = DjangoFilterBackend().filter_queryset(request, queryset, self)

            queryset = filters.SearchFilter().filter_queryset(request, queryset, self)
        else:
            queryset = self.filter_queryset(self.get_queryset())

        locations = list(queryset)

        for location in locations:
            views = get_location_views_last_7_days(location.id)

            location.popularity = calculate_location_popularity(location.rating, location.reviews_count, views)

        if ordering == "-popularity":
            locations.sort(key=lambda location: location.popularity, reverse=True)
        elif ordering == "popularity":
            locations.sort(key=lambda location: location.popularity)

        page = self.paginate_queryset(locations)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            response_data = self.get_serializer(locations, many=True).data

        cache.set(cache_key, response_data, timeout=60)

        return Response(response_data)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        invalidate_location_cache()

    def perform_update(self, serializer):
        serializer.save()
        invalidate_location_cache()

    def perform_destroy(self, instance):
        instance.soft_delete()
        invalidate_location_cache()


    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        locations = self.filter_queryset(self.get_queryset())

        for location in locations:
            views = get_location_views_last_7_days(location.id)

            location.popularity = calculate_location_popularity(
                rating=location.rating,
                reviews_count=location.reviews_count,
                views_last_7_days=views,
            )

        export_format = request.query_params.get("export_format", "json")

        if export_format == "csv":
            return export_locations_csv(locations)

        if export_format == "json":
            serializer = self.get_serializer(locations, many=True)
            return Response(serializer.data)

        return Response(
            {
                "detail": "Unsupported export format. Use json or csv."
            },
            status=400,
        )