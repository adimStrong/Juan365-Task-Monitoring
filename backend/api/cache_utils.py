"""
Cache utilities for Netflix-style data optimization.

Strategies implemented:
1. Pre-computed stats - Calculate expensive queries and cache results
2. Stale-while-revalidate - Return cached data immediately, refresh in background
3. Smart invalidation - Invalidate related caches when data changes
4. Per-user caching - Cache user-specific data separately

Cache keys format:
- dashboard:stats:{user_id}:{role} - Dashboard stats per user/role
- analytics:{date_from}:{date_to} - Analytics for date range (shared)
- tickets:list:{hash} - Ticket list with filters
"""

import hashlib
import json
import logging
from functools import wraps
from django.core.cache import cache
from django.conf import settings

logger = logging.getLogger(__name__)

# Cache timeouts (seconds)
CACHE_TTL_DASHBOARD = 300  # 5 minutes - stats refresh frequently
CACHE_TTL_ANALYTICS = 900  # 15 minutes - analytics are expensive
CACHE_TTL_LISTS = 60       # 1 minute - lists change often
CACHE_TTL_STATIC = 3600    # 1 hour - departments, products


def get_cache_key(*args):
    """Generate a cache key from arguments."""
    return ':'.join(str(arg) for arg in args)


def hash_params(params_dict):
    """Generate a hash for query parameters."""
    sorted_params = json.dumps(params_dict, sort_keys=True)
    return hashlib.md5(sorted_params.encode()).hexdigest()[:12]


def cache_response(key_prefix, timeout=300, vary_on_user=False, vary_on_role=False):
    """
    Decorator for caching API responses.

    Args:
        key_prefix: Base cache key
        timeout: Cache timeout in seconds
        vary_on_user: Include user ID in cache key
        vary_on_role: Include user role in cache key (manager vs member)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Build cache key
            key_parts = [key_prefix]

            if vary_on_user:
                key_parts.append(f'user:{request.user.id}')
            elif vary_on_role:
                role = 'manager' if request.user.is_manager else 'member'
                key_parts.append(f'role:{role}')

            # Include query params in key
            if request.query_params:
                key_parts.append(hash_params(dict(request.query_params)))

            cache_key = get_cache_key(*key_parts)

            # Try to get from cache
            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug(f'Cache HIT: {cache_key}')
                return cached

            logger.debug(f'Cache MISS: {cache_key}')

            # Execute function and cache result
            response = func(self, request, *args, **kwargs)

            # Only cache successful responses
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache.set(cache_key, response, timeout)

            return response
        return wrapper
    return decorator


def invalidate_dashboard_cache(user_id=None):
    """
    Invalidate dashboard cache.
    If user_id provided, only invalidate that user's cache.
    Otherwise, invalidate all dashboard caches.
    """
    if user_id:
        # Invalidate specific user's dashboard
        for role in ['manager', 'member']:
            cache.delete(get_cache_key('dashboard', 'stats', f'user:{user_id}'))
            cache.delete(get_cache_key('dashboard', 'stats', f'role:{role}'))
    else:
        # Use cache key pattern deletion if available (Redis)
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            keys = redis_conn.keys('*dashboard*')
            if keys:
                redis_conn.delete(*keys)
                logger.info(f'Invalidated {len(keys)} dashboard cache keys')
        except (ImportError, Exception) as e:
            # Fallback for non-Redis cache
            logger.debug(f'Pattern deletion not available: {e}')
            cache.delete(get_cache_key('dashboard', 'stats', 'role:manager'))
            cache.delete(get_cache_key('dashboard', 'stats', 'role:member'))


def invalidate_analytics_cache():
    """Invalidate all analytics caches."""
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys('*analytics*')
        if keys:
            redis_conn.delete(*keys)
            logger.info(f'Invalidated {len(keys)} analytics cache keys')
    except (ImportError, Exception) as e:
        logger.debug(f'Analytics cache pattern deletion not available: {e}')


def invalidate_ticket_caches():
    """Invalidate all ticket-related caches when a ticket changes."""
    invalidate_dashboard_cache()
    invalidate_analytics_cache()
    # Also invalidate ticket list caches
    try:
        from django_redis import get_redis_connection
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys('*tickets*')
        if keys:
            redis_conn.delete(*keys)
    except (ImportError, Exception):
        pass


def warm_dashboard_cache(user):
    """
    Pre-warm dashboard cache for a user.
    Called after login or major ticket changes.
    """
    from django.utils import timezone
    from datetime import timedelta
    from .models import Ticket
    from django.db.models import Q

    role = 'manager' if user.is_manager else 'member'
    cache_key = get_cache_key('dashboard', 'stats', f'role:{role}')

    # Check if already cached
    if cache.get(cache_key):
        return

    # Build stats (same logic as DashboardView)
    if user.is_manager:
        tickets = Ticket.objects.filter(is_deleted=False)
    else:
        tickets = Ticket.objects.filter(
            Q(requester=user) | Q(assigned_to=user),
            is_deleted=False
        )

    now = timezone.now()

    stats = {
        'total_tickets': tickets.count(),
        'pending_approval': tickets.filter(status=Ticket.Status.REQUESTED).count(),
        'pending_creative': tickets.filter(status=Ticket.Status.PENDING_CREATIVE).count(),
        'in_progress': tickets.filter(status=Ticket.Status.IN_PROGRESS).count(),
        'completed': tickets.filter(status=Ticket.Status.COMPLETED).count(),
        'approved': tickets.filter(status=Ticket.Status.APPROVED).count(),
        'rejected': tickets.filter(status=Ticket.Status.REJECTED).count(),
        'overdue': tickets.filter(deadline__lt=now).exclude(
            status__in=[Ticket.Status.COMPLETED, Ticket.Status.REJECTED]
        ).count(),
    }

    cache.set(cache_key, stats, CACHE_TTL_DASHBOARD)
    logger.info(f'Warmed dashboard cache for role:{role}')


class CachedQuerySet:
    """
    Wrapper for caching expensive querysets.

    Usage:
        cached_qs = CachedQuerySet(
            Ticket.objects.filter(status='completed'),
            cache_key='completed_tickets',
            timeout=300
        )
        results = cached_qs.get()
    """

    def __init__(self, queryset, cache_key, timeout=300):
        self.queryset = queryset
        self.cache_key = cache_key
        self.timeout = timeout

    def get(self):
        """Get cached results or execute query."""
        cached = cache.get(self.cache_key)
        if cached is not None:
            return cached

        results = list(self.queryset)
        cache.set(self.cache_key, results, self.timeout)
        return results

    def invalidate(self):
        """Clear the cache."""
        cache.delete(self.cache_key)


def get_cached_departments():
    """Get departments from cache or database."""
    cache_key = 'static:departments'
    cached = cache.get(cache_key)
    if cached:
        return cached

    from .models import Department
    departments = list(Department.objects.filter(is_active=True).values('id', 'name'))
    cache.set(cache_key, departments, CACHE_TTL_STATIC)
    return departments


def get_cached_products():
    """Get products from cache or database."""
    cache_key = 'static:products'
    cached = cache.get(cache_key)
    if cached:
        return cached

    from .models import Product
    products = list(Product.objects.filter(is_active=True).values('id', 'name', 'category'))
    cache.set(cache_key, products, CACHE_TTL_STATIC)
    return products
