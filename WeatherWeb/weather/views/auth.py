"""
Authentication Views – Login, Register, Logout, Email Verification, Change Password, Change Email

Routing rules after authentication:
  - Staff / Superuser / profile.role == 'admin'  →  /panel/   (AdminPanel dashboard)
  - Regular user                                  →  /         (Map page)

Email verification flow:
  1. Register  → account created with is_active=False + verification email sent
  2. User clicks link → EmailVerifyView validates token → is_active=True
  3. LoginView: if password OK but is_active=False → friendly unverified-email message

Change email flow:
  1. Authenticated user visits /change-email/ and submits new email
  2. Confirmation email sent to the NEW address
  3. User clicks link → ChangeEmailConfirmView updates user.email
"""
import uuid

from django.contrib.auth import (
    authenticate,
    login,
    logout,
    update_session_auth_hash,
    get_user_model,
)
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.views import View

from weather.models import EmailVerificationToken, EmailChangeToken


User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redirect_after_login(user, next_url=None):
    """
    Return the appropriate redirect URL for *user* once they have logged in.
    Priority: explicit ?next= param → role-based default.
    """
    if next_url and next_url not in ('/', ''):
        return next_url
    if user.is_staff or user.is_superuser:
        return '/panel/'
    try:
        if user.profile.role == 'admin':
            return '/panel/'
    except Exception:
        pass
    return '/'


def _get_or_create_token(user):
    """Delete any existing token and create a fresh one."""
    EmailVerificationToken.objects.filter(user=user).delete()
    return EmailVerificationToken.objects.create(user=user)


def _send_verification_email(request, user, token_obj):
    """Send the account-activation email to *user*."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = str(token_obj.token)
    verify_url = request.build_absolute_uri(
        f'/verify-email/{uid}/{token}/'
    )
    subject = 'WeatherGIS – Xác thực địa chỉ email của bạn'
    html_body = render_to_string('email/verification_email.html', {
        'user': user,
        'verify_url': verify_url,
        'expiry_hours': EmailVerificationToken.TOKEN_EXPIRY_HOURS,
    })
    plain_body = (
        f'Xin chào {user.username},\n\n'
        f'Vui lòng click vào đường link sau để xác thực email:\n{verify_url}\n\n'
        f'Link có hiệu lực trong {EmailVerificationToken.TOKEN_EXPIRY_HOURS} giờ.\n\n'
        'Nếu bạn không đăng ký tài khoản WeatherGIS, hãy bỏ qua email này.'
    )
    send_mail(
        subject=subject,
        message=plain_body,
        from_email=None,  # uses DEFAULT_FROM_EMAIL from settings
        recipient_list=[user.email],
        html_message=html_body,
        fail_silently=False,
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginView(View):
    """User login view – redirects based on role after successful auth."""
    template_name = 'auth/login.html'

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

        # Check whether the account exists but is inactive
        existing_user = User.objects.filter(username=username).first()
        if existing_user and existing_user.check_password(password) and not existing_user.is_active:
            # Distinguish: never verified vs manually deactivated by admin
            has_token = EmailVerificationToken.objects.filter(user=existing_user).exists()
            if has_token:
                return render(request, self.template_name, {
                    'error': 'Tài khoản chưa xác thực email. Vui lòng kiểm tra hộp thư của bạn hoặc',
                    'show_resend': True,
                    'resend_username': username,
                })
            return render(request, self.template_name, {
                'error': 'Tài khoản đang bị vô hiệu hóa. Vui lòng liên hệ quản trị viên.',
            })

        return render(request, self.template_name, {
            'error': 'Tên đăng nhập hoặc mật khẩu không đúng',
        })


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class RegisterView(View):
    """
    User registration view.
    New users are created with is_active=False; a verification email is sent.
    """
    template_name = 'auth/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(_redirect_after_login(request.user))
        return render(request, self.template_name)

    def post(self, request):
        username  = request.POST.get('username', '').strip()
        email     = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        form_data = {'username': username, 'email': email}

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

        # Create inactive user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=False,
        )
        # Ensure UserProfile exists
        try:
            from weather.models import UserProfile
            UserProfile.objects.get_or_create(user=user, defaults={'role': UserProfile.ROLE_USER})
        except Exception:
            pass

        # Create verification token + send email
        try:
            token_obj = _get_or_create_token(user)
            _send_verification_email(request, user, token_obj)
        except Exception as exc:
            # If email sending fails, delete the user and show error
            user.delete()
            return render(request, self.template_name, {
                'error': f'Không thể gửi email xác thực. Vui lòng thử lại sau. ({exc})',
                'form_data': form_data,
            })

        request.session['pending_verify_email'] = email
        return redirect('register-pending')


# ---------------------------------------------------------------------------
# Register Pending (check inbox page)
# ---------------------------------------------------------------------------

class RegisterPendingView(View):
    """Shown after registration - tells user to check email."""
    template_name = 'auth/register_pending.html'

    def get(self, request):
        email = request.session.get('pending_verify_email', '')
        return render(request, self.template_name, {'email': email})


# ---------------------------------------------------------------------------
# Email Verification
# ---------------------------------------------------------------------------

class EmailVerifyView(View):
    """
    Validates the token from the email link.
    GET /verify-email/<uidb64>/<token>/
    """
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return render(request, 'auth/email_verify_invalid.html', {
                'reason': 'Link không hợp lệ hoặc đã bị xoá.',
            })

        try:
            token_obj = EmailVerificationToken.objects.get(user=user, token=token)
        except EmailVerificationToken.DoesNotExist:
            return render(request, 'auth/email_verify_invalid.html', {
                'reason': 'Link đã được sử dụng hoặc không tồn tại.',
            })

        if token_obj.is_expired():
            return render(request, 'auth/email_verify_invalid.html', {
                'reason': f'Link đã hết hạn (hiệu lực {EmailVerificationToken.TOKEN_EXPIRY_HOURS} giờ).',
                'show_resend': True,
                'user_id': user.pk,
            })

        # Activate user
        user.is_active = True
        user.save(update_fields=['is_active'])
        token_obj.delete()

        return render(request, 'auth/email_verify_success.html', {
            'username': user.username,
        })


# ---------------------------------------------------------------------------
# Resend Verification Email
# ---------------------------------------------------------------------------

class ResendVerificationView(View):
    """
    POST /resend-verification/ — resend the verification email.
    Accepts username or email in POST body.
    """
    def post(self, request):
        identifier = (
            request.POST.get('username', '') or
            request.POST.get('email', '')
        ).strip()

        if not identifier:
            return redirect('login')

        user = (
            User.objects.filter(username=identifier).first() or
            User.objects.filter(email__iexact=identifier).first()
        )

        if not user:
            return render(request, 'auth/register_pending.html', {
                'error': 'Không tìm thấy tài khoản.',
                'email': identifier,
            })

        if user.is_active:
            return redirect('login')

        try:
            token_obj = _get_or_create_token(user)
            _send_verification_email(request, user, token_obj)
            request.session['pending_verify_email'] = user.email
        except Exception as exc:
            return render(request, 'auth/register_pending.html', {
                'error': f'Không thể gửi email. Vui lòng thử lại sau. ({exc})',
                'email': user.email,
            })

        return render(request, 'auth/register_pending.html', {
            'email': user.email,
            'resent': True,
        })


# ---------------------------------------------------------------------------
# Change Password (authenticated users)
# ---------------------------------------------------------------------------

class ChangePasswordView(View):
    """Allow an authenticated user to change their own password."""
    template_name = 'auth/change_password.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        current_password = request.POST.get('current_password', '')
        new_password     = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not current_password or not new_password or not confirm_password:
            return render(request, self.template_name, {
                'error': 'Vui lòng điền đầy đủ các trường.',
            })

        if not request.user.check_password(current_password):
            return render(request, self.template_name, {
                'error': 'Mật khẩu hiện tại không đúng.',
            })

        if new_password != confirm_password:
            return render(request, self.template_name, {
                'error': 'Mật khẩu mới và xác nhận không khớp.',
            })

        if len(new_password) < 6:
            return render(request, self.template_name, {
                'error': 'Mật khẩu mới phải có ít nhất 6 ký tự.',
            })

        if new_password == current_password:
            return render(request, self.template_name, {
                'error': 'Mật khẩu mới phải khác mật khẩu hiện tại.',
            })

        request.user.set_password(new_password)
        request.user.save()
        # Keep the user logged in after password change
        update_session_auth_hash(request, request.user)

        return render(request, self.template_name, {
            'success': 'Mật khẩu đã được thay đổi thành công.',
        })


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutView(View):
    """Log out and return to map page."""
    def get(self, request):
        logout(request)
        return redirect('map')

    def post(self, request):
        logout(request)
        return redirect('map')


# ---------------------------------------------------------------------------
# Change Email (authenticated users)
# ---------------------------------------------------------------------------

def _send_email_change_confirmation(request, user, token_obj):
    """Send confirmation email to the NEW address before it is applied."""
    uid   = urlsafe_base64_encode(force_bytes(user.pk))
    token = str(token_obj.token)
    confirm_url = request.build_absolute_uri(
        f'/confirm-email-change/{uid}/{token}/'
    )
    subject = 'WeatherGIS – Xác nhận thay đổi địa chỉ email'
    html_body = render_to_string('email/email_change_confirmation.html', {
        'user': user,
        'new_email': token_obj.new_email,
        'confirm_url': confirm_url,
        'expiry_hours': EmailChangeToken.TOKEN_EXPIRY_HOURS,
    })
    plain_body = (
        f'Xin chào {user.username},\n\n'
        f'Bạn (hoặc ai đó) đã yêu cầu thay đổi email sang: {token_obj.new_email}\n'
        f'Click để xác nhận: {confirm_url}\n\n'
        f'Link có hiệu lực trong {EmailChangeToken.TOKEN_EXPIRY_HOURS} giờ.\n'
        'Nếu bạn không yêu cầu điều này, hãy bỏ qua email này.'
    )
    send_mail(
        subject=subject,
        message=plain_body,
        from_email=None,
        recipient_list=[token_obj.new_email],
        html_message=html_body,
        fail_silently=False,
    )


class ChangeEmailView(View):
    """
    Authenticated user requests an email address change.
    A confirmation link is sent to the NEW email before it is applied.
    """
    template_name = 'auth/change_email.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        new_email = request.POST.get('new_email', '').strip()
        password  = request.POST.get('password', '')

        if not new_email or not password:
            return render(request, self.template_name, {
                'error': 'Vui lòng nhập địa chỉ email mới và mật khẩu hiện tại.',
            })

        try:
            validate_email(new_email)
        except ValidationError:
            return render(request, self.template_name, {
                'error': 'Email không hợp lệ.',
            })

        if not request.user.check_password(password):
            return render(request, self.template_name, {
                'error': 'Mật khẩu hiện tại không đúng.',
            })

        if new_email.lower() == request.user.email.lower():
            return render(request, self.template_name, {
                'error': 'Email mới phải khác email hiện tại.',
            })

        if User.objects.filter(email__iexact=new_email).exclude(pk=request.user.pk).exists():
            return render(request, self.template_name, {
                'error': 'Email này đã được sử dụng bởi tài khoản khác.',
            })

        # Create/replace change token
        try:
            token_obj = EmailChangeToken.objects.create_for_user(request.user, new_email)
            _send_email_change_confirmation(request, request.user, token_obj)
        except Exception as exc:
            return render(request, self.template_name, {
                'error': f'Không thể gử email xác nhận. Vui lòng thử lại. ({exc})',
            })

        return render(request, self.template_name, {
            'sent': True,
            'new_email': new_email,
        })


class ChangeEmailConfirmView(View):
    """
    Validates the token from the new-email confirmation link.
    GET /confirm-email-change/<uidb64>/<token>/
    """
    def get(self, request, uidb64, token):
        try:
            uid  = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return render(request, 'auth/change_email_invalid.html', {
                'reason': 'Link không hợp lệ.',
            })

        try:
            token_obj = EmailChangeToken.objects.get(user=user, token=token)
        except EmailChangeToken.DoesNotExist:
            return render(request, 'auth/change_email_invalid.html', {
                'reason': 'Link đã được sử dụng hoặc không tồn tại.',
            })

        if token_obj.is_expired():
            token_obj.delete()
            return render(request, 'auth/change_email_invalid.html', {
                'reason': f'Link đã hết hạn ({EmailChangeToken.TOKEN_EXPIRY_HOURS} giờ).',
            })

        new_email = token_obj.new_email
        user.email = new_email
        user.save(update_fields=['email'])
        token_obj.delete()

        return render(request, 'auth/change_email_success.html', {
            'new_email': new_email,
        })


# ---------------------------------------------------------------------------
# Profile (General)
# ---------------------------------------------------------------------------

class ProfileView(View):
    """General user profile view accessible to all logged-in users."""
    template_name = 'auth/profile.html'

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect(f'/login/?next={request.path}')

        try:
            from weather.models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
        except Exception:
            profile = None

        return render(request, self.template_name, {
            'target_user': request.user,
            'profile': profile,
        })

