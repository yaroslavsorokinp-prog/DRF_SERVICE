from django.db import models


class LocationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)

    def deleted(self):
        return self.filter(is_deleted=True)

    def delete(self):
        return self.update(is_deleted=True)


class LocationManager(models.Manager):
    def get_queryset(self):
        return LocationQuerySet(self.model, using=self._db).active()