from django.conf import settings
from django.db import models

from .managers import LocationManager


class Location(models.Model):
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="locations",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    name = models.CharField(max_length=255)
    description = models.TextField()
    address = models.CharField(max_length=500)

    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_deleted = models.BooleanField(default=False)

    objects = LocationManager()
    all_objects = models.Manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])