from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='following_set')
    followee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='followers_set')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'followee'], name='unique_follow'),
            models.CheckConstraint(condition=~Q(follower=F('followee')), name='no_self_follow'),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower.username} follows {self.followee.username}'
