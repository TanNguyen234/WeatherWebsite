"""
Authentication Views - Login, Register, Logout

Routing rules after authentication:
  - Staff / Superuser / profile.role == 'admin'  →  /panel/   (AdminPanel dashboard)
  - Regular user                                  →  /         (Map page)
"""
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User


def _redirect_after_login(user, next_url=None):
    """
    Return the appropriate redirect URL for *user* once they have logged in.
    Priority: explicit ?next= param → role-based default.

    URL mapping (from WeatherWeb/urls.py + adminpanel/urls.py):
      - Map page        : path('', ...)  → /
      - Admin dashboard : path('panel/', include(...))  + path('', ...) → /panel/
    """
    if next_url and next_url not in ('/', ''):
        return next_url
    if user.is_staff or user.is_superuser:
        return '/panel/'
    # Also check the profile role (non-staff admin in the profile table)
    try:
        if user.profile.role == 'admin':
            return '/panel/'
    except Exception:
        pass
    return '/'   # root URL = MapView


class LoginView(View):
    """
    User login view – redirects based on role after successful auth.
    """
    template_name = "auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_redirect_after_login(request.user))
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', '')
            return redirect(_redirect_after_login(user, next_url))

        return render(request, self.template_name, {
            'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
        })


class RegisterView(View):
    """
    User registration view.
    New registrations are always regular users → redirect to /map/.
    """
    template_name = "auth/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_redirect_after_login(request.user))
        return render(request, self.template_name)

    def post(self, request):
        username  = request.POST.get('username', '').strip()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        if not username or not password:
            return render(request, self.template_name, {
                'error': 'Tên đăng nhập và mật khẩu là bắt buộc'
            })

        if password != password2:
            return render(request, self.template_name, {
                'error': 'Mật khẩu không khớp'
            })

        if User.objects.filter(username=username).exists():
            return render(request, self.template_name, {
                'error': 'Tên đăng nhập đã tồn tại'
            })

        user = User.objects.create_user(username=username, password=password)
        # Ensure a UserProfile exists for the new user
        try:
            from weather.models import UserProfile
            UserProfile.objects.get_or_create(user=user, defaults={'role': UserProfile.ROLE_USER})
        except Exception:
            pass

        login(request, user)
        return redirect('map')


class LogoutView(View):
    """Log out and return to map page."""
    def get(self, request):
        logout(request)
        return redirect('map')
    
    def post(self, request):
        logout(request)
        return redirect('map')
