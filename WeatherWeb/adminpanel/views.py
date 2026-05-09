"""
Admin Panel Views – WeatherGIS

Provides a staff-only dashboard with:
  - System overview metrics
  - User management table (list + toggle active)
  - Saved location browser
  - Route browser
  - API health check
  - Layer configuration viewer

Architecture:
  - All views are class-based and inherit AdminBaseView to enforce staff-only access.
  - Business logic is minimal; views delegate to services and model queries.
  - No business logic is duplicated here; service layer owns logic.
"""
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import os
import requests

from weather.models import UserLocation, Route, AboutContent
from weather.models import UserLocation, Route, AboutContent

User = get_user_model()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")


# ---------------------------------------------------------------------------
# Access control mixin
# ---------------------------------------------------------------------------

class AdminBaseView(View):
    """
    Base class for all admin panel views.
    Requires the request user to be authenticated AND to be staff, superuser,
    or to have a UserProfile with role == 'admin'.
    Users that do not pass this check are redirected to /login/.
    (The DEBUG bypass has been removed – auth is always enforced.)
    """
    login_url = '/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'{self.login_url}?next={request.path}')
        if not self._is_admin(request.user):
            # Authenticated but not admin → send back to the map
            return redirect('map')
        return super().dispatch(request, *args, **kwargs)

    @staticmethod
    def _is_admin(user):
        """Return True when the user has admin-level access."""
        if user.is_staff or user.is_superuser:
            return True
        try:
            return user.profile.role == 'admin'
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(AdminBaseView):
    """Main admin dashboard – full user directory with attributes."""

    template_name = 'adminpanel/dashboard.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()

        total_users     = User.objects.count()
        active_users    = User.objects.filter(is_active=True).count()
        staff_users     = User.objects.filter(is_staff=True).count()
        total_locations = UserLocation.objects.count()
        total_routes    = Route.objects.count()

        # All users (with optional search)
        qs = User.objects.order_by('-date_joined')
        if query:
            qs = qs.filter(username__icontains=query) | qs.filter(email__icontains=query)

        user_list = []
        for u in qs:
            user_list.append({
                'user':           u,
                'location_count': UserLocation.objects.filter(user=u).count(),
                'route_count':    Route.objects.filter(user=u).count(),
            })

        # API status (fast check, no tile ping on dashboard)
        api_status = _check_api_status()

        context = {
            'stats': {
                'total_users':     total_users,
                'active_users':    active_users,
                'inactive_users':  total_users - active_users,
                'staff_users':     staff_users,
                'total_locations': total_locations,
                'total_routes':    total_routes,
            },
            'users':      user_list,
            'query':      query,
            'api_status': api_status,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserListView(AdminBaseView):
    """List all users with key attributes."""

    template_name = 'adminpanel/users.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        users = User.objects.order_by('-date_joined')
        if query:
            users = users.filter(username__icontains=query) | \
                    users.filter(email__icontains=query)

        # Annotate each user with location count
        user_list = []
        for u in users:
            user_list.append({
                'user':            u,
                'location_count':  UserLocation.objects.filter(user=u).count(),
                'route_count':     Route.objects.filter(user=u).count(),
            })

        context = {
            'users': user_list,
            'query': query,
        }
        return render(request, self.template_name, context)


class UserDetailView(AdminBaseView):
    """Detailed view for a single user with real data from DB."""

    template_name = 'adminpanel/user_detail.html'

    def get(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)

        try:
            profile = target_user.profile
        except Exception:
            profile = None

        locations = UserLocation.objects.filter(user=target_user).order_by('-created_at')[:20]
        routes = Route.objects.select_related('start_location', 'end_location').filter(user=target_user).order_by('-created_at')[:20]

        context = {
            'target_user': target_user,
            'profile': profile,
            'locations': locations,
            'routes': routes,
            'location_count': UserLocation.objects.filter(user=target_user).count(),
            'route_count': Route.objects.filter(user=target_user).count(),
        }
        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name='dispatch')
class UserToggleActiveView(AdminBaseView):
    """Toggle a user's is_active status via POST (AJAX)."""

    def post(self, request):
        if not self._is_admin(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)

        user_id = request.POST.get('user_id') or request.GET.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'user_id requis'}, status=400)
        target = get_object_or_404(User, pk=user_id)

        # Prevent deactivating own account
        if target == request.user:
            return JsonResponse({'error': 'Không thể vô hiệu hoá tài khoản của chính bạn'}, status=400)

        target.is_active = not target.is_active
        target.save(update_fields=['is_active'])

        return JsonResponse({'success': True, 'is_active': target.is_active})


@method_decorator(csrf_exempt, name='dispatch')
class UserDeleteView(AdminBaseView):
    """Delete a user via POST (AJAX)."""

    def post(self, request):
        if not self._is_admin(request.user):
            return JsonResponse({'error': 'Forbidden'}, status=403)

        user_id = request.POST.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Thiếu user_id'}, status=400)
        target = get_object_or_404(User, pk=user_id)

        if target == request.user:
            return JsonResponse({'error': 'Không thể xóa tài khoản của chính bạn'}, status=400)

        target.delete()
        return JsonResponse({'success': True})


# ---------------------------------------------------------------------------
# User Edit (Role / Permission assignment)
# ---------------------------------------------------------------------------

class UserEditView(AdminBaseView):
    """Form to edit a user's role, is_staff, is_active flags."""

    template_name = 'adminpanel/user_edit.html'

    def get(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)
        try:
            profile = target_user.profile
        except Exception:
            profile = None
        return render(request, self.template_name, {
            'target_user': target_user,
            'profile': profile,
        })

    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)

        # Guard: cannot edit own account via this form
        if target_user == request.user:
            return redirect('adminpanel:user-detail', user_id=user_id)

        is_active  = request.POST.get('is_active') == 'on'
        is_staff   = request.POST.get('is_staff') == 'on'
        # Only superuser may set/unset superuser flag
        is_superuser = target_user.is_superuser
        if request.user.is_superuser:
            is_superuser = request.POST.get('is_superuser') == 'on'

        new_role = request.POST.get('role', 'user')
        if new_role not in ('user', 'admin'):
            new_role = 'user'

        with transaction.atomic():
            target_user.is_active    = is_active
            target_user.is_staff     = is_staff
            target_user.is_superuser = is_superuser
            target_user.save(update_fields=['is_active', 'is_staff', 'is_superuser'])

            try:
                from weather.models import UserProfile
                profile, _ = UserProfile.objects.get_or_create(
                    user=target_user,
                    defaults={'role': new_role},
                )
                profile.role = new_role
                profile.save(update_fields=['role'])
            except Exception:
                pass

        return redirect('adminpanel:user-detail', user_id=user_id)


@method_decorator(csrf_exempt, name='dispatch')
class UserRoleUpdateView(AdminBaseView):
    """Quick AJAX role toggle from the user list table."""

    def post(self, request, user_id):
        target_user = get_object_or_404(User, pk=user_id)

        if target_user == request.user:
            return JsonResponse({'error': 'Không thể thạy đổi quyền của chính mình'}, status=400)

        new_role = request.POST.get('role', 'user')
        if new_role not in ('user', 'admin'):
            return JsonResponse({'error': 'Vai trò không hợp lệ'}, status=400)

        with transaction.atomic():
            from weather.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=target_user)
            profile.role = new_role
            profile.save(update_fields=['role'])
            # Sync is_staff with admin role
            target_user.is_staff = (new_role == 'admin')
            target_user.save(update_fields=['is_staff'])

        return JsonResponse({'success': True, 'role': new_role})


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

class LocationListView(AdminBaseView):
    """Browse all saved user locations."""

    template_name = 'adminpanel/locations.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        locations = UserLocation.objects.select_related('user').order_by('-created_at')
        if query:
            locations = locations.filter(name__icontains=query) | \
                        locations.filter(user__username__icontains=query)

        context = {
            'locations': locations[:200],
            'total':     UserLocation.objects.count(),
            'query':     query,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

class RouteListView(AdminBaseView):
    """Browse all saved routes."""

    template_name = 'adminpanel/routes.html'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        qs = Route.objects.select_related(
            'user', 'start_location', 'end_location'
        ).order_by('-created_at')
        if query:
            qs = qs.filter(name__icontains=query) | \
                 qs.filter(user__username__icontains=query)

        routes = []
        for r in qs[:200]:
            routes.append({
                'route':    r,
                'start':    r.start_location,
                'end':      r.end_location,
                'created_at': r.created_at,
                'distance_km': None,
            })

        context = {
            'routes': routes,
            'total':  Route.objects.count(),
            'query':  query,
        }
        return render(request, self.template_name, context)


# ---------------------------------------------------------------------------
# API Health
# ---------------------------------------------------------------------------

class APIHealthView(AdminBaseView):
    """Live API health check endpoint."""

    template_name = 'adminpanel/api_health.html'

    def get(self, request):
        status = _check_api_status()
        context = {'api_status': status}
        return render(request, self.template_name, context)


@method_decorator(csrf_exempt, name='dispatch')
class APIHealthCheckView(AdminBaseView):
    """JSON endpoint to re-run API health check (used by JS)."""

    def get(self, request):
        status = _check_api_status()
        return JsonResponse(status)


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_api_status() -> dict:
    """
    Ping OpenWeatherMap /weather and map tiles endpoint.
    Returns a dict shaped for both the dashboard template and the JS health check:
      {
        'owm':   { ok, latency_ms, has_key, error, response_preview },
        'tiles': { ok, latency_ms, error },
        # Legacy / dashboard keys:
        'owm_ok', 'owm_latency_ms', 'owm_error', 'has_key'
      }
    """
    import time

    has_key = bool(OPENWEATHER_API_KEY)
    owm  = {'ok': False, 'latency_ms': None, 'has_key': has_key, 'error': None, 'response_preview': None}
    tiles = {'ok': False, 'latency_ms': None, 'error': None}

    # ── OWM current-weather ping ─────────────────────────────
    if has_key:
        try:
            t0 = time.monotonic()
            resp = requests.get(
                'https://api.openweathermap.org/data/2.5/weather',
                params={
                    'lat':   21.0285,
                    'lon':   105.8542,
                    'appid': OPENWEATHER_API_KEY,
                    'units': 'metric',
                },
                timeout=8,
            )
            owm['latency_ms'] = round((time.monotonic() - t0) * 1000)
            if resp.status_code == 200:
                owm['ok'] = True
                try:
                    owm['response_preview'] = resp.json()
                except Exception:
                    pass
            elif resp.status_code == 401:
                owm['error'] = 'API key không hợp lệ (401)'
            else:
                owm['error'] = f'HTTP {resp.status_code}'
        except requests.Timeout:
            owm['error'] = 'Timeout'
        except Exception as exc:
            owm['error'] = str(exc)
    else:
        owm['error'] = 'API key chưa cấu hình'

    # ── Tile server ping (no key needed for HEAD) ─────────────
    try:
        t0 = time.monotonic()
        resp = requests.head(
            'https://tile.openweathermap.org/map/temp_new/5/25/15.png',
            timeout=6,
        )
        tiles['latency_ms'] = round((time.monotonic() - t0) * 1000)
        # OWM tile server returns 200 or 400 (bad key) – both mean it's reachable
        tiles['ok'] = resp.status_code in (200, 400)
        if not tiles['ok']:
            tiles['error'] = f'HTTP {resp.status_code}'
    except requests.Timeout:
        tiles['error'] = 'Timeout'
    except Exception as exc:
        tiles['error'] = str(exc)

    return {
        'owm':   owm,
        'tiles': tiles,
        # Flat keys for dashboard template
        'owm_ok':         owm['ok'],
        'owm_latency_ms': owm['latency_ms'],
        'owm_error':      owm['error'],
        'has_key':        has_key,
    }


# ---------------------------------------------------------------------------
# About Page CMS
# ---------------------------------------------------------------------------

class AboutContentListView(AdminBaseView):
    """List all About page content blocks for admin management."""

    template_name = 'adminpanel/about_content.html'

    def get(self, request):
        blocks = AboutContent.objects.order_by('order', 'key')
        return render(request, self.template_name, {'blocks': blocks})


class AboutContentCreateView(AdminBaseView):
    """Create a new About page content block."""

    template_name = 'adminpanel/about_content_form.html'

    def get(self, request):
        return render(request, self.template_name, {
            'content_block': None,
            'form_data': {'key': '', 'title': '', 'body': '', 'order': 0, 'is_visible': True}
        })

    def post(self, request):
        key        = request.POST.get('key', '').strip()
        title      = request.POST.get('title', '').strip()
        body       = request.POST.get('body', '').strip()
        order      = request.POST.get('order', '0').strip()
        is_visible = request.POST.get('is_visible') == 'on'

        errors = []
        if not key:
            errors.append('Định danh (key) là bắt buộc.')
        if not title:
            errors.append('Tiêu đề là bắt buộc.')
        if AboutContent.objects.filter(key=key).exists():
            errors.append(f'Key "{key}" đã tồn tại.')

        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            return render(request, self.template_name, {
                'content_block': None,
                'errors': errors,
                'form_data': request.POST,
            })

        AboutContent.objects.create(
            key=key,
            title=title,
            body=body,
            order=order,
            is_visible=is_visible,
            updated_by=request.user,
        )
        return redirect('adminpanel:about-content')


class AboutContentEditView(AdminBaseView):
    """Edit an existing About page content block."""

    template_name = 'adminpanel/about_content_form.html'

    def get(self, request, pk):
        content_block = get_object_or_404(AboutContent, pk=pk)
        return render(request, self.template_name, {
            'content_block': content_block,
            'form_data': {
                'title': content_block.title,
                'body': content_block.body,
                'order': content_block.order,
                'is_visible': content_block.is_visible,
            }
        })

    def post(self, request, pk):
        content_block = get_object_or_404(AboutContent, pk=pk)
        title      = request.POST.get('title', '').strip()
        body       = request.POST.get('body', '').strip()
        order      = request.POST.get('order', '0').strip()
        is_visible = request.POST.get('is_visible') == 'on'

        errors = []
        if not title:
            errors.append('Tiêu đề là bắt buộc.')

        try:
            order = int(order)
        except ValueError:
            order = 0

        if errors:
            return render(request, self.template_name, {
                'content_block': content_block,
                'errors': errors,
                'form_data': request.POST,
            })

        content_block.title      = title
        content_block.body       = body
        content_block.order      = order
        content_block.is_visible = is_visible
        content_block.updated_by = request.user
        content_block.save()

        return redirect('adminpanel:about-content')


@method_decorator(csrf_exempt, name='dispatch')
class AboutContentDeleteView(AdminBaseView):
    """Delete an About page content block via POST."""

    def post(self, request, pk):
        block = get_object_or_404(AboutContent, pk=pk)
        block.delete()
        return redirect('adminpanel:about-content')


@method_decorator(csrf_exempt, name='dispatch')
class AboutContentReorderView(AdminBaseView):
    """
    AJAX endpoint to update ordering.
    Expects POST body: { "order": [{"id": 1, "order": 0}, ...] }
    """

    def post(self, request):
        import json
        try:
            data = json.loads(request.body)
            items = data.get('order', [])
            for item in items:
                AboutContent.objects.filter(pk=item['id']).update(order=item['order'])
            return JsonResponse({'success': True})
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=400)

