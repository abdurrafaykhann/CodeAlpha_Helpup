from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.HelpupLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),  # POST only (Django 5)
    path('settings/', views.profile_edit, name='profile_edit'),
    path('u/<str:username>/', views.profile_detail, name='profile'),
]
