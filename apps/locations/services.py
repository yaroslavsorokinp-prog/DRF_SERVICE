import logging
import time

from django.core.cache import cache
from django_redis import get_redis_connection
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import RedisError


logger = logging.getLogger(__name__)

VIEW_TTL = 60 * 60
VIEWS_7_DAYS = 60 * 60 * 24 * 7


def get_viewer_key(request):
    if request.user.is_authenticated:
        return f"user:{request.user.id}"

    if not request.session.session_key:
        request.session.create()

    return f"session:{request.session.session_key}"


def register_location_view(location_id, request):
    redis = get_redis_connection("default")

    viewer_key = get_viewer_key(request)

    throttle_key = f"location:{location_id}:viewed:{viewer_key}"

    views_key = f"location:{location_id}:views"

    if redis.exists(throttle_key):
        return False

    now = int(time.time())
    view_id = f"{viewer_key}:{now}"

    redis.zadd(views_key, {view_id: now})
    redis.expire(views_key, VIEWS_7_DAYS)
    redis.set(throttle_key, "1", ex=VIEW_TTL)

    return True


def calculate_location_popularity(rating, reviews_count, views_last_7_days):
    rating = rating or 0
    reviews_count = reviews_count or 0

    return rating * 10 + reviews_count * 2 + views_last_7_days


def get_location_views_last_7_days(location_id):
    redis = get_redis_connection("default")

    views_key = f"location:{location_id}:views"

    now = int(time.time())
    seven_days_ago = now - VIEWS_7_DAYS

    redis.zremrangebyscore(views_key, 0, seven_days_ago)

    return redis.zcard(views_key)


def invalidate_location_cache():
    try:
        cache.delete_pattern("locations:list:*")
    except (ConnectionInterrupted, RedisError, TimeoutError):
        # Cache invalidation is best-effort: Redis being unavailable must not
        # turn a successfully saved location/review into an API error.
        logger.exception("Could not invalidate the locations list cache")
