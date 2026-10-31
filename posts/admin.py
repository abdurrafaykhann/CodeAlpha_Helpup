from django.contrib import admin

from .models import Comment, Like, Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'short_text', 'has_image', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username')
    date_hierarchy = 'created_at'
    raw_id_fields = ('author',)

    @admin.display(description='Text')
    def short_text(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text

    @admin.display(boolean=True, description='Image')
    def has_image(self, obj):
        return bool(obj.image)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'post', 'text', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username')
    raw_id_fields = ('author', 'post')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username',)
    raw_id_fields = ('user', 'post')
