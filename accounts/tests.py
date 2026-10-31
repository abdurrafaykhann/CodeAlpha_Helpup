from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from config.test_helpers import PASSWORD, HelpupTestCase, User, make_image, make_oversized_image, make_user

from .models import Profile


class AuthenticationTests(HelpupTestCase):
    def register(self, **overrides):
        data = {'username': 'newuser', 'full_name': 'New User', 'email': 'new@example.com', 'password1': PASSWORD, 'password2': PASSWORD}
        data.update(overrides)
        return self.client.post(reverse('accounts:register'), data)

    def test_register_creates_user_profile_and_logs_in(self):
        response = self.register()
        self.assertRedirects(response, reverse('accounts:profile_edit'))
        user = User.objects.get(username='newuser')
        self.assertEqual(user.profile.full_name, 'New User')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_every_user_gets_a_one_to_one_profile(self):
        user = User.objects.create_user('shell_user', password=PASSWORD)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_password_validation(self):
        for password, expected in [('short1', 'too short'), ('password', 'too common'), ('12345678', 'entirely numeric')]:
            response = self.register(password1=password, password2=password)
            self.assertEqual(response.status_code, 200, password)
            self.assertContains(response, expected, msg_prefix=password)
        response = self.register(password2='different-Pass-1')
        self.assertContains(response, "didn")  # "The two password fields didn't match."
        self.assertFalse(User.objects.filter(username='newuser').exists())

    def test_duplicate_username_is_rejected_case_insensitively(self):
        make_user('taken')
        response = self.register(username='TAKEN')
        self.assertContains(response, 'already taken')

    def test_login_and_logout(self):
        make_user('walker')
        bad = self.client.post(reverse('accounts:login'), {'username': 'walker', 'password': 'wrong'})
        self.assertContains(bad, 'Please enter a correct username and password')
        good = self.client.post(reverse('accounts:login'), {'username': 'walker', 'password': PASSWORD})
        self.assertRedirects(good, reverse('home'), fetch_redirect_response=False)
        self.assertIn('_auth_user_id', self.client.session)

        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)  # logout is POST only
        self.client.post(reverse('accounts:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_protected_pages_require_login(self):
        user = make_user('someone')
        protected = [
            reverse('social:explore'), reverse('social:nearby'), reverse('notifications:list'), reverse('posts:create'),
            reverse('accounts:profile_edit'), reverse('accounts:profile', args=['someone']),
            reverse('social:followers', args=['someone']),
        ]
        for url in protected:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse('accounts:login'), response['Location'], url)
        self.assertEqual(self.client.post(reverse('social:follow', args=[user.username])).status_code, 302)

    def test_anonymous_home_shows_landing_page(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'Connect beyond')


class ProfileTests(HelpupTestCase):
    def setUp(self):
        self.user = make_user('editor')
        self.login(self.user)

    def test_edit_profile_saves_fields_and_normalises_interests(self):
        response = self.client.post(reverse('accounts:profile_edit'), {
            'full_name': 'Edit Or', 'bio': 'Hello there', 'city': '  Lahore ', 'neighbourhood': 'Gulberg',
            'interests': 'Hiking, coffee , hiking,  ', 'show_in_nearby': 'on',
        })
        self.assertRedirects(response, reverse('accounts:profile', args=['editor']))
        profile = Profile.objects.get(user=self.user)
        self.assertEqual((profile.full_name, profile.city, profile.neighbourhood), ('Edit Or', 'Lahore', 'Gulberg'))
        self.assertEqual(profile.interests, 'Hiking, coffee')
        self.assertTrue(profile.show_in_nearby)

    def test_opting_out_of_nearby(self):
        self.client.post(reverse('accounts:profile_edit'), {'full_name': 'x', 'city': 'Lahore'})  # checkbox omitted = off
        self.assertFalse(Profile.objects.get(user=self.user).show_in_nearby)

    def test_upload_avatar(self):
        self.client.post(reverse('accounts:profile_edit'), {'avatar': make_image('me.png'), 'show_in_nearby': 'on'})
        profile = Profile.objects.get(user=self.user)
        self.assertTrue(profile.avatar.name.startswith('avatars/'))
        page = self.client.get(reverse('accounts:profile', args=['editor']))
        self.assertContains(page, profile.avatar.url)

    def test_invalid_avatar_files_are_rejected(self):
        not_image = SimpleUploadedFile('evil.txt', b'hello', content_type='text/plain')
        response = self.client.post(reverse('accounts:profile_edit'), {'avatar': not_image})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['avatar'])

        fake_png = SimpleUploadedFile('fake.png', b'this is not an image', content_type='image/png')
        response = self.client.post(reverse('accounts:profile_edit'), {'avatar': fake_png})
        self.assertTrue(response.context['form'].errors['avatar'])

        response = self.client.post(reverse('accounts:profile_edit'), {'avatar': make_oversized_image('big.png')})
        self.assertIn('too large', str(response.context['form'].errors['avatar']))
        self.assertFalse(Profile.objects.get(user=self.user).avatar)

    def test_view_other_profiles(self):
        make_user('someone_else', full_name='Some One')
        response = self.client.get(reverse('accounts:profile', args=['someone_else']))
        self.assertContains(response, 'Some One')
        self.assertEqual(self.client.get(reverse('accounts:profile', args=['nobody'])).status_code, 404)
