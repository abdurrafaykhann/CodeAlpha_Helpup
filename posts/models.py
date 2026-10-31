from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, Exists, OuterRef
from django.urls import reverse

from accounts.validators import validate_image


class PostQuerySet(models.QuerySet):
    def with_stats(self, user):
        """Attach author, like/comment counts and whether `user` has liked each post."""
        return self.select_related('author', 'author__profile').annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True),
            liked=Exists(Like.objects.filter(post=OuterRef('pk'), user=user)),
        )


class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    text = models.TextField(max_length=1000, blank=True)
    image = models.ImageField(upload_to='posts/%Y/%m/', blank=True, validators=[validate_image])
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = PostQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post {self.pk} by {self.author.username}'

    def clean(self):
        if not self.text.strip() and not self.image:
            raise ValidationError('Write something or attach an image to publish a post.')

    def get_absolute_url(self):
        return reverse('posts:detail', args=[self.pk])

    @property
    def was_edited(self):
        return (self.updated_at - self.created_at).total_seconds() > 60


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments')
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'Comment {self.pk} on post {self.post_id}'


class Like(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'post'], name='unique_like_per_user_post')]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} likes post {self.post_id}'
