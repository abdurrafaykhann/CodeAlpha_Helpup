from django.db import IntegrityError, transaction
from django.urls import reverse

from config.test_helpers import AJAX, HelpupTestCase, make_user
from notifications.models import Notification
from posts.models import Post

from .models import Follow


class FollowTests(HelpupTestCase):
    def setUp(self):
        self.me = make_user('me')
        self.them = make_user('them')
        self.login(self.me)
        self.url = reverse('social:follow', args=['them'])

    def test_follow_and_unfollow_via_json(self):
        self.assertEqual(self.client.post(self.url, **AJAX).json(), {'following': True, 'followers_count': 1})
        self.assertTrue(Follow.objects.filter(follower=self.me, followee=self.them).exists())
        self.assertEqual(self.client.post(self.url, **AJAX).json(), {'following': False, 'followers_count': 0})
        self.assertFalse(Follow.objects.exists())

    def test_cannot_follow_yourself(self):
        response = self.client.post(reverse('social:follow', args=['me']), **AJAX)
        self.assertEqual(response.status_code, 400)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Follow.objects.create(follower=self.me, followee=self.me)  # database-level guarantee
        self.assertEqual(Follow.objects.count(), 0)

    def test_duplicate_follow_relationships_are_impossible(self):
        Follow.objects.create(follower=self.me, followee=self.them)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Follow.objects.create(follower=self.me, followee=self.them)

    def test_follow_notifies_and_unfollow_retracts(self):
        self.client.post(self.url, **AJAX)
        note = Notification.objects.get()
        self.assertEqual((note.recipient, note.actor, note.verb), (self.them, self.me, Notification.FOLLOW))
        self.client.post(self.url, **AJAX)
        self.assertEqual(Notification.objects.count(), 0)

    def test_counts_and_lists(self):
        third = make_user('third')
        Follow.objects.create(follower=self.me, followee=self.them)
        Follow.objects.create(follower=third, followee=self.them)
        profile = self.client.get(reverse('accounts:profile', args=['them']))
        self.assertEqual(profile.context['followers_count'], 2)
        self.assertTrue(profile.context['is_following'])
        followers = self.client.get(reverse('social:followers', args=['them']))
        self.assertEqual({u.username for u in followers.context['page']}, {'me', 'third'})
        following = self.client.get(reverse('social:following', args=['me']))
        self.assertEqual([u.username for u in following.context['page']], ['them'])

    def test_follow_requires_post(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)


class FeedTests(HelpupTestCase):
    def setUp(self):
        self.me = make_user('me', city='Lahore', interests='coffee')
        self.friend = make_user('friend')
        self.stranger = make_user('stranger', city='Lahore', interests='coffee')
        Follow.objects.create(follower=self.me, followee=self.friend)
        self.mine = Post.objects.create(author=self.me, text='my own post')
        self.friends = Post.objects.create(author=self.friend, text='friend post')
        self.strangers = Post.objects.create(author=self.stranger, text='stranger post')
        self.login(self.me)

    def test_following_tab_shows_self_and_followed_only(self):
        page = self.client.get(reverse('home')).context['page']
        self.assertEqual({p.text for p in page}, {'my own post', 'friend post'})

    def test_latest_tab_shows_everyone(self):
        page = self.client.get(reverse('home') + '?tab=latest').context['page']
        self.assertEqual(len(list(page)), 3)

    def test_thin_feed_gets_recommendations(self):
        recommended = self.client.get(reverse('home')).context['recommended']
        self.assertEqual([p.text for p in recommended], ['stranger post'])

    def test_feed_cards_show_counts(self):
        self.assertContains(self.client.get(reverse('home')), 'data-like-count')


class ExploreTests(HelpupTestCase):
    def setUp(self):
        self.me = make_user('me')
        alice = make_user('alice_dev', full_name='Alice Developer', interests='coding, music')
        make_user('bob', full_name='Bob Builder', city='Karachi')
        self.post = Post.objects.create(author=alice, text='Django tips and tricks')
        Post.objects.create(author=alice, text='Something else entirely')
        self.login(self.me)

    def test_search_people(self):
        for q in ('alice', 'Developer', 'music', 'karachi'):
            result = self.client.get(reverse('social:explore'), {'q': q, 'scope': 'people'}).context['people']
            self.assertEqual(len(list(result)), 1, q)
        self.assertEqual(len(list(self.client.get(reverse('social:explore'), {'q': 'zzzz'}).context['people'])), 0)

    def test_search_posts(self):
        posts = self.client.get(reverse('social:explore'), {'q': 'django', 'scope': 'posts'}).context['posts']
        self.assertEqual([p.pk for p in posts], [self.post.pk])

    def test_default_explore_shows_suggestions_and_recent_posts(self):
        context = self.client.get(reverse('social:explore')).context
        self.assertGreaterEqual(len(context['suggestions']), 2)
        self.assertEqual(len(list(context['recent'])), 2)


class NearbyTests(HelpupTestCase):
    def setUp(self):
        self.me = make_user('me', city='Lahore', neighbourhood='Gulberg', interests='coffee, hiking')
        self.near = make_user('near', city='Lahore', neighbourhood='Gulberg', interests='Hiking, books')
        self.city_only = make_user('city_only', city='lahore', neighbourhood='DHA', interests='cricket')
        self.far = make_user('far', city='Karachi', neighbourhood='Clifton', interests='hiking')
        self.hidden = make_user('hidden', city='Lahore', neighbourhood='Gulberg', show_in_nearby=False)
        self.login(self.me)

    def names(self, **params):
        response = self.client.get(reverse('social:nearby'), params)
        return [c['user'].username for c in response.context['cards']]

    def test_defaults_to_my_city_and_ranks_by_closeness(self):
        names = self.names()
        self.assertEqual(names, ['near', 'city_only'])  # same neighbourhood first; case-insensitive city match

    def test_filter_by_city_neighbourhood_and_interest(self):
        self.assertEqual(self.names(city='Karachi'), ['far'])
        self.assertEqual(self.names(city='Lahore', neighbourhood='DHA'), ['city_only'])
        self.assertEqual(self.names(city='', interest='hiking'), ['near', 'far'])
        self.assertEqual(self.names(city='Lahore', interest='hiking'), ['near'])
        self.assertEqual(self.names(city='Nowhere'), [])

    def test_shared_interests_are_reported(self):
        cards = self.client.get(reverse('social:nearby')).context['cards']
        self.assertEqual(cards[0]['shared'], ['hiking'])

    def test_users_who_opt_out_never_appear(self):
        self.assertNotIn('hidden', self.names(city=''))
        self.assertNotIn('me', self.names(city=''))
        self.assertNotContains(self.client.get(reverse('social:nearby'), {'city': ''}), '@hidden')

    def test_only_city_and_neighbourhood_are_exposed(self):
        html = self.client.get(reverse('social:nearby')).content.decode()
        self.assertIn('Gulberg', html)
        field_names = {f.name for f in type(self.me.profile)._meta.get_fields()}
        self.assertFalse({'address', 'latitude', 'longitude', 'street', 'phone'} & field_names)

    def test_filters_list_only_visible_locations(self):
        context = self.client.get(reverse('social:nearby'), {'city': ''}).context
        self.assertEqual(context['cities'], ['Karachi', 'Lahore'])


class NotificationTests(HelpupTestCase):
    def setUp(self):
        self.me = make_user('me')
        self.fan = make_user('fan')
        self.post = Post.objects.create(author=self.me, text='hello')
        self.login(self.fan)
        self.client.post(reverse('social:follow', args=['me']), **AJAX)
        self.client.post(reverse('posts:like', args=[self.post.pk]), **AJAX)
        self.client.post(reverse('posts:comment_add', args=[self.post.pk]), {'text': 'hey'}, **AJAX)
        self.login(self.me)

    def test_unread_count_in_navigation_and_json(self):
        self.assertEqual(self.client.get(reverse('notifications:count')).json(), {'count': 3})
        self.assertContains(self.client.get(reverse('social:explore')), 'data-notif-badge')
        self.assertEqual(self.client.get(reverse('social:explore')).context['unread_count'], 3)

    def test_list_shows_all_event_types_then_marks_read(self):
        response = self.client.get(reverse('notifications:list'))
        for text in ('started following you', 'liked your post', 'commented on your post'):
            self.assertContains(response, text)
        self.assertEqual(len(response.context['unread_ids']), 3)
        self.assertEqual(self.client.get(reverse('notifications:count')).json(), {'count': 0})

    def test_mark_all_read(self):
        self.client.post(reverse('notifications:mark_all_read'))
        self.assertEqual(Notification.objects.filter(is_read=False).count(), 0)

    def test_notifications_are_private(self):
        self.login(self.fan)
        self.assertEqual(self.client.get(reverse('notifications:count')).json(), {'count': 0})
        self.assertNotContains(self.client.get(reverse('notifications:list')), 'liked your post')
