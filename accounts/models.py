from django.conf import settings
from django.db import models

from .validators import validate_image


class Profile(models.Model):
    """Extra information for every user. Created automatically (see signals.py)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    full_name = models.CharField(max_length=80, blank=True)
    bio = models.CharField(max_length=300, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, validators=[validate_image])
    city = models.CharField(max_length=80, blank=True, db_index=True)
    neighbourhood = models.CharField(max_length=80, blank=True)
    interests = models.CharField(max_length=200, blank=True, help_text='Comma-separated, e.g. "photography, hiking"')
    show_in_nearby = models.BooleanField(
        default=True, help_text='Let people find you on the Nearby page (only your city and neighbourhood are shown).'
    )

    class Meta:
        ordering = ['user__username']

    def __str__(self):
        return f'Profile of {self.user.username}'

    @property
    def display_name(self):
        return self.full_name or self.user.username

    @property
    def initials(self):
        source = self.display_name.strip() or '?'
        return source[0].upper()

    @property
    def hue(self):
        """Stable colour for the placeholder avatar."""
        return sum(ord(c) * (i + 3) for i, c in enumerate(self.user.username)) % 360

    @property
    def interest_list(self):
        seen, result = set(), []
        for raw in self.interests.split(','):
            item = raw.strip().lower()
            if item and item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @property
    def location_label(self):
        return ', '.join(part for part in (self.neighbourhood, self.city) if part)
