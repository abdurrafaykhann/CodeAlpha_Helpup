from django.contrib import admin

from .models import Follow


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'followee', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('follower__username', 'followee__username')
    raw_id_fields = ('follower', 'followee')
