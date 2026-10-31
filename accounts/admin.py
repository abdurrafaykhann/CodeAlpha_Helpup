from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin

from .models import Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


admin.site.unregister(User)


@admin.register(User)
class HelpupUserAdmin(UserAdmin):
    inlines = [ProfileInline]
    list_display = ('username', 'email', 'is_staff', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'profile__full_name', 'profile__city')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'city', 'neighbourhood', 'show_in_nearby')
    list_filter = ('show_in_nearby', 'city')
    search_fields = ('user__username', 'full_name', 'city', 'neighbourhood', 'interests')
    autocomplete_fields = ('user',)
