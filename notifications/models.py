from django.conf import settings
from django.db import models


class Notification(models.Model):
    FOLLOW = 'follow'
    LIKE = 'like'
    COMMENT = 'comment'
    VERB_CHOICES = [(FOLLOW, 'started following you'), (LIKE, 'liked your post'), (COMMENT, 'commented on your post')]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='+')
    verb = models.CharField(max_length=10, choices=VERB_CHOICES)
    post = models.ForeignKey('posts.Post', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f'{self.actor.username} {self.get_verb_display()} -> {self.recipient.username}'
