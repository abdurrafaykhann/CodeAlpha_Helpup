"""Shared helpers for the test suites."""
import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

User = get_user_model()
PASSWORD = 'Sup3r-secret-pass'
AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

_MEDIA = tempfile.mkdtemp(prefix='helpup-test-media-')


def make_image(name='photo.png', size=(24, 24), fmt='PNG', color='red'):
    buffer = BytesIO()
    Image.new('RGB', size, color).save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{fmt.lower()}')


def make_oversized_image(name='huge.png'):
    """A genuinely valid PNG padded with trailing bytes to just over the 5 MB limit."""
    valid = make_image(name).read()
    return SimpleUploadedFile(name, valid + b'\0' * (5 * 1024 * 1024 + 1), content_type='image/png')


def make_user(username, **profile):
    user = User.objects.create_user(username=username, password=PASSWORD)
    if profile:
        for key, value in profile.items():
            setattr(user.profile, key, value)
        user.profile.save()
    return user


@override_settings(MEDIA_ROOT=_MEDIA, PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])  # fast hashing in tests
class HelpupTestCase(TestCase):
    """TestCase that stores uploads in a throw-away folder."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password=PASSWORD))
