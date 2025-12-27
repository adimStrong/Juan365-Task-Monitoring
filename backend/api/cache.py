"""
Caching utilities for the API.
Provides cache decorators and helper functions for invalidation.
"""
from functools import wraps
from django.core.cache import cache
from django.conf import settings


# Cache key prefixes
CACHE_KEYS = {
    'departments': 'departments_list',
    'products': 'products_list',
    'users': 'users_list_{user_id}',
    'ticket': 'ticket_{ticket_id}',
    'tickets_list': 'tickets_list_{user_id}_{params}',
    'dashboard': 'dashboard_{user_id}',
    'analytics': 'analytics_{params}',
}


def get_cache_timeout(cache_type='medium'):
    """Get cache timeout based on type."""
    timeouts = {
        'short': getattr(settings, 'CACHE_TTL_SHORT', 60),
        'medium': getattr(settings, 'CACHE_TTL_MEDIUM', 300),
        'long': getattr(settings, 'CACHE_TTL_LONG', 3600),
    }
    return timeouts.get(cache_type, 300)


def cache_response(key_prefix, timeout='medium', vary_on_user=False):
    """
    Decorator to cache view responses.

    Args:
        key_prefix: Cache key prefix
        timeout: 'short', 'medium', or 'long'
        vary_on_user: If True, cache varies per user
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            # Build cache key
            cache_key = key_prefix
            if vary_on_user and request.user.is_authenticated:
                cache_key = f"{key_prefix}_user_{request.user.id}"

            # Add query params to key for list views
            if request.query_params:
                params_str = '_'.join(f"{k}={v}" for k, v in sorted(request.query_params.items()))
                cache_key = f"{cache_key}_{params_str}"

            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                return cached_response

            # Execute view and cache result
            response = view_func(self, request, *args, **kwargs)

            # Only cache successful responses
            if response.status_code == 200:
                cache.set(cache_key, response, get_cache_timeout(timeout))

            return response
        return wrapper
    return decorator


def invalidate_ticket_cache(ticket_id=None, user_id=None):
    """Invalidate ticket-related caches."""
    patterns_to_delete = []

    if ticket_id:
        patterns_to_delete.append(f"ticket_{ticket_id}")

    # Invalidate list caches - these will regenerate on next request
    # Using cache.delete_pattern if available (Redis), else just delete known keys
    try:
        cache.delete_pattern('tickets_list_*')
        cache.delete_pattern('dashboard_*')
    except AttributeError:
        # Fallback for non-Redis cache
        if user_id:
            cache.delete(f"tickets_list_{user_id}")
            cache.delete(f"dashboard_{user_id}")


def invalidate_static_cache():
    """Invalidate static data caches (departments, products, users)."""
    cache.delete('departments_list')
    cache.delete('products_list')
    try:
        cache.delete_pattern('users_list_*')
    except AttributeError:
        pass


def warm_cache():
    """Pre-warm frequently accessed caches."""
    from .models import Department, Product

    # Cache departments
    departments = list(Department.objects.filter(is_active=True))
    cache.set('departments_list', departments, get_cache_timeout('long'))

    # Cache products
    products = list(Product.objects.filter(is_active=True))
    cache.set('products_list', products, get_cache_timeout('long'))
