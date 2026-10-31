from django.urls import path

from . import views

app_name = 'posts'

urlpatterns = [
    path('new/', views.post_create, name='create'),
    path('<int:pk>/', views.post_detail, name='detail'),
    path('<int:pk>/edit/', views.post_edit, name='edit'),
    path('<int:pk>/delete/', views.post_delete, name='delete'),
    path('<int:pk>/like/', views.like_toggle, name='like'),
    path('<int:pk>/comments/', views.comment_list, name='comments'),
    path('<int:pk>/comments/add/', views.comment_add, name='comment_add'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
]
