from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.http import JsonResponse
import json

@csrf_protect
def login_view(request):
    """
    Handle user login
    """
    if request.user.is_authenticated:
        return redirect('claims_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name or user.username}!')
                next_url = request.GET.get('next', 'claims_list')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please enter both username and password.')
    
    return render(request, 'auth/login.html')

@csrf_protect
def signup_view(request):
    """
    Handle user registration
    """
    if request.user.is_authenticated:
        return redirect('claims_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validation
        if not all([username, email, first_name, password, password_confirm]):
            messages.error(request, 'Please fill in all required fields.')
        elif password != password_confirm:
            messages.error(request, 'Passwords do not match.')
        elif len(password) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
        else:
            # Create user
            try:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name or ''
                )
                login(request, user)
                messages.success(request, f'Welcome to ERISA Recovery, {user.first_name}!')
                return redirect('claims_list')
            except Exception as e:
                messages.error(request, 'An error occurred during registration. Please try again.')
    
    return render(request, 'auth/signup.html')

def logout_view(request):
    """
    Handle user logout
    """
    if request.user.is_authenticated:
        username = request.user.first_name or request.user.username
        logout(request)
        messages.success(request, f'Goodbye, {username}! You have been logged out.')
    
    return redirect('login')
