from .models import Notification


def notify(recipient, actor, verb, post=None):
    """Create a notification, never notifying people about their own actions."""
    if recipient == actor:
        return None
    return Notification.objects.create(recipient=recipient, actor=actor, verb=verb, post=post)


def retract(recipient, actor, verb, post=None):
    """Remove a notification when the action is undone (unlike / unfollow)."""
    Notification.objects.filter(recipient=recipient, actor=actor, verb=verb, post=post).delete()
