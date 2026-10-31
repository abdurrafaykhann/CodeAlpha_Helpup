from django.urls import path

from . import views

app_name = 'social'

urlpatterns = [
    path('explore/', views.explore, name='explore'),
    path('nearby/', views.nearby, name='nearby'),
    path('u/<str:username>/follow/', views.follow_toggle, name='follow'),
    path('u/<str:username>/followers/', views.followers_list, name='followers'),
    path('u/<str:username>/following/', views.following_list, name='following'),
]
