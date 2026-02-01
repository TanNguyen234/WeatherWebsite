"""
Authentication Views - Login, Register, Logout
"""
from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User


class LoginView(View):
    """
    User login view
    """
    template_name = "auth/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('map')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'map')
            return redirect(next_url)
        
        return render(request, self.template_name, {
            'error': 'Tên đăng nhập hoặc mật khẩu không đúng'
        })


class RegisterView(View):
    """
    User registration view
    """
    template_name = "auth/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('map')
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
          # Validation
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
        
        # Create user
        user = User.objects.create_user(username=username, password=password)
        login(request, user)
        
        return redirect('map')


class LogoutView(View):
    """
    User logout view
    """
    def get(self, request):
        logout(request)
        return redirect('map')
    
    def post(self, request):
        logout(request)
        return redirect('map')
