from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.urls import reverse

from config.test_helpers import AJAX, HelpupTestCase, make_image, make_oversized_image, make_user
from notifications.models import Notification

from .models import Comment, Like, Post


class PostTests(HelpupTestCase):
    def setUp(self):
        self.author = make_user('author')
        self.other = make_user('other')
        self.login(self.author)

    def test_create_text_post(self):
        response = self.client.post(reverse('posts:create'), {'text': '  Hello HELPUP  '})
        self.assertRedirects(response, reverse('home'))
        post = Post.objects.get()
        self.assertEqual((post.author, post.text), (self.author, 'Hello HELPUP'))

    def test_create_post_with_image_stores_the_file(self):
        self.client.post(reverse('posts:create'), {'text': 'With picture', 'image': make_image('pic.png')})
        post = Post.objects.get()
        self.assertTrue(post.image.name.startswith('posts/'))
        self.assertTrue(post.image.storage.exists(post.image.name))
        self.assertContains(self.client.get(reverse('posts:detail', args=[post.pk])), post.image.url)

    def test_image_only_post_is_allowed(self):
        self.client.post(reverse('posts:create'), {'image': make_image()})
        self.assertEqual(Post.objects.count(), 1)

    def test_empty_post_is_rejected(self):
        response = self.client.post(reverse('posts:create'), {'text': '   '})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Write something or attach an image')
        self.assertEqual(Post.objects.count(), 0)

    def test_invalid_images_are_rejected(self):
        for upload in (
            SimpleUploadedFile('notes.txt', b'plain text', content_type='text/plain'),
            SimpleUploadedFile('fake.png', b'not really a png', content_type='image/png'),
            SimpleUploadedFile('vector.svg', b'<svg xmlns="http://www.w3.org/2000/svg"/>', content_type='image/svg+xml'),
        ):
            response = self.client.post(reverse('posts:create'), {'text': 'x', 'image': upload})
            self.assertEqual(response.status_code, 200, upload.name)
            self.assertTrue(response.context['form'].errors['image'], upload.name)
        response = self.client.post(reverse('posts:create'), {'text': 'x', 'image': make_oversized_image()})
        self.assertIn('too large', str(response.context['form'].errors['image']))
        self.assertEqual(Post.objects.count(), 0)

    def test_owner_can_edit_and_delete(self):
        post = Post.objects.create(author=self.author, text='first draft')
        self.client.post(reverse('posts:edit', args=[post.pk]), {'text': 'second draft'})
        post.refresh_from_db()
        self.assertEqual(post.text, 'second draft')
        # confirmation page does not delete; POST does
        self.assertEqual(self.client.get(reverse('posts:delete', args=[post.pk])).status_code, 200)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())
        self.client.post(reverse('posts:delete', args=[post.pk]))
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_users_cannot_edit_or_delete_other_peoples_posts(self):
        post = Post.objects.create(author=self.other, text='not yours')
        for url in (reverse('posts:edit', args=[post.pk]), reverse('posts:delete', args=[post.pk])):
            self.assertEqual(self.client.get(url).status_code, 403, url)
            self.assertEqual(self.client.post(url, {'text': 'hacked'}).status_code, 403, url)
        post.refresh_from_db()
        self.assertEqual(post.text, 'not yours')
        self.assertContains(self.client.get(reverse('posts:edit', args=[post.pk])), 'only change your own posts', status_code=403)

    def test_edit_and_delete_links_only_shown_to_owner(self):
        post = Post.objects.create(author=self.other, text='someone elses')
        self.assertNotContains(self.client.get(reverse('posts:detail', args=[post.pk])), reverse('posts:edit', args=[post.pk]))


class LikeTests(HelpupTestCase):
    def setUp(self):
        self.author = make_user('author')
        self.fan = make_user('fan')
        self.post = Post.objects.create(author=self.author, text='like me')
        self.url = reverse('posts:like', args=[self.post.pk])
        self.login(self.fan)

    def test_like_and_unlike_via_json(self):
        data = self.client.post(self.url, **AJAX).json()
        self.assertEqual(data, {'liked': True, 'count': 1})
        data = self.client.post(self.url, **AJAX).json()
        self.assertEqual(data, {'liked': False, 'count': 0})
        self.assertEqual(Like.objects.count(), 0)

    def test_duplicate_likes_are_impossible(self):
        Like.objects.create(user=self.fan, post=self.post)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Like.objects.create(user=self.fan, post=self.post)

    def test_like_requires_post_and_csrf(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        from django.test import Client
        strict = Client(enforce_csrf_checks=True)
        strict.login(username='fan', password='Sup3r-secret-pass')
        self.assertEqual(strict.post(self.url).status_code, 403)
        self.assertEqual(Like.objects.count(), 0)

    def test_like_notifies_author_and_unlike_retracts(self):
        self.client.post(self.url, **AJAX)
        note = Notification.objects.get()
        self.assertEqual((note.recipient, note.actor, note.verb, note.post), (self.author, self.fan, Notification.LIKE, self.post))
        self.client.post(self.url, **AJAX)
        self.assertEqual(Notification.objects.count(), 0)

    def test_liking_your_own_post_does_not_notify(self):
        self.login(self.author)
        self.client.post(self.url, **AJAX)
        self.assertEqual(Notification.objects.count(), 0)

    def test_liked_state_is_rendered(self):
        Like.objects.create(user=self.fan, post=self.post)
        html = self.client.get(reverse('posts:detail', args=[self.post.pk])).content.decode()
        self.assertIn('act like on', html)


class CommentTests(HelpupTestCase):
    def setUp(self):
        self.author = make_user('author')
        self.visitor = make_user('visitor')
        self.post = Post.objects.create(author=self.author, text='comment on me')
        self.add_url = reverse('posts:comment_add', args=[self.post.pk])
        self.login(self.visitor)

    def test_add_comment_via_json(self):
        response = self.client.post(self.add_url, {'text': 'Nice post!'}, **AJAX)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertIn('Nice post!', data['html'])
        self.assertIn('visitor', data['html'])
        self.assertEqual(Comment.objects.get().author, self.visitor)

    def test_empty_comments_are_rejected(self):
        for text in ('', '    '):
            response = self.client.post(self.add_url, {'text': text}, **AJAX)
            self.assertEqual(response.status_code, 400)
            self.assertIn('empty', response.json()['error'])
        self.assertEqual(Comment.objects.count(), 0)

    def test_comment_notifies_post_author(self):
        self.client.post(self.add_url, {'text': 'hi'}, **AJAX)
        note = Notification.objects.get()
        self.assertEqual((note.recipient, note.actor, note.verb), (self.author, self.visitor, Notification.COMMENT))

    def test_comments_listing_and_detail_page(self):
        Comment.objects.create(post=self.post, author=self.author, text='first!')
        self.assertIn('first!', self.client.get(reverse('posts:comments', args=[self.post.pk])).json()['html'])
        self.assertContains(self.client.get(self.post.get_absolute_url()), 'first!')

    def test_delete_own_comment_only(self):
        mine = Comment.objects.create(post=self.post, author=self.visitor, text='mine')
        theirs = Comment.objects.create(post=self.post, author=self.author, text='theirs')
        denied = self.client.post(reverse('posts:comment_delete', args=[theirs.pk]), **AJAX)
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=theirs.pk).exists())
        ok = self.client.post(reverse('posts:comment_delete', args=[mine.pk]), **AJAX)
        self.assertEqual((ok.status_code, ok.json()['count']), (200, 1))
        self.assertFalse(Comment.objects.filter(pk=mine.pk).exists())
