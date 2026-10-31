from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from posts import views as post_views

handler403 = 'config.views.permission_denied'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', post_views.home, name='home'),
    path('accounts/', include('accounts.urls')),
    path('posts/', include('posts.urls')),
    path('notifications/', include('notifications.urls')),
    path('', include('social.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
