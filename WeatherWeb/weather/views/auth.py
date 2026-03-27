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
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


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

        existing_user = User.objects.filter(username=username).first()
        if existing_user and existing_user.check_password(password) and not existing_user.is_active:
            return render(request, self.template_name, {
                'error': 'Tài khoản đang bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.'
            })

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
        email = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        form_data = {
            'username': username,
            'email': email,
        }

        if not username or not email or not password:
            return render(request, self.template_name, {
                'error': 'Tên đăng nhập, email và mật khẩu là bắt buộc',
                'form_data': form_data,
            })

        try:
            validate_email(email)
        except ValidationError:
            return render(request, self.template_name, {
                'error': 'Email không hợp lệ',
                'form_data': form_data,
            })

        if password != password2:
            return render(request, self.template_name, {
                'error': 'Mật khẩu không khớp',
                'form_data': form_data,
            })

        if User.objects.filter(username=username).exists():
            return render(request, self.template_name, {
                'error': 'Tên đăng nhập đã tồn tại',
                'form_data': form_data,
            })

        if User.objects.filter(email__iexact=email).exists():
            return render(request, self.template_name, {
                'error': 'Email đã được sử dụng',
                'form_data': form_data,
            })

        user = User.objects.create_user(username=username, email=email, password=password)
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
