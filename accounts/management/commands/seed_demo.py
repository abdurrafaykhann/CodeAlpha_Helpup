"""DEMO DATA ONLY - fills a development database with sample people and posts.

Usage:
    python manage.py seed_demo            # create demo data (skipped if it already exists)
    python manage.py seed_demo --reset    # delete the demo users first, then recreate them

All demo accounts share the password printed at the end. Never run this against production data.
"""
import io
import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from notifications.models import Notification
from notifications.services import notify
from posts.models import Comment, Like, Post
from social.models import Follow

User = get_user_model()
DEMO_PASSWORD = 'helpup123'

# username, full name, bio, city, neighbourhood, interests, hue
PEOPLE = [
    ('aisha_k', 'Aisha Khan', 'Coffee, code and long walks. Building things for the web.', 'Lahore', 'Gulberg', 'coding, coffee, hiking', 200),
    ('bilal_ahmed', 'Bilal Ahmed', 'Weekend cricketer. Weekday product manager.', 'Lahore', 'DHA', 'cricket, startups, travel', 25),
    ('sana_codes', 'Sana Malik', 'Frontend dev. Dark mode evangelist.', 'Lahore', 'Johar Town', 'coding, design, books', 280),
    ('hamza_lens', 'Hamza Raza', 'Street photographer. Chasing golden hour.', 'Lahore', 'Gulberg', 'photography, travel, coffee', 330),
    ('mehr_bakes', 'Mehr Fatima', 'Home baker. Sourdough is a lifestyle.', 'Lahore', 'Model Town', 'baking, food, gardening', 45),
    ('usman_fit', 'Usman Tariq', 'Gym, gym and more gym. Free weekend runs.', 'Karachi', 'Clifton', 'fitness, running, football', 5),
    ('zara_art', 'Zara Hussain', 'Illustrator. Watercolours and tiny cats.', 'Karachi', 'DHA', 'art, design, books', 300),
    ('omar_trails', 'Omar Sheikh', 'Hiker and trail runner. North is home.', 'Islamabad', 'F-7', 'hiking, photography, running', 140),
    ('hira_reads', 'Hira Nasir', 'Bookworm. Currently on book 47 this year.', 'Islamabad', 'G-11', 'books, coffee, writing', 340),
    ('danish_dev', 'Danish Iqbal', 'Backend engineer. Django fan since 2015.', 'Islamabad', 'F-7', 'coding, startups, football', 220),
    ('noor_cafe', 'Noor Ali', 'Barista and café owner. Ask me about beans.', 'Karachi', 'Clifton', 'coffee, food, music', 30),
    ('faisal_fc', 'Faisal Qureshi', 'Football coach. Sunday league legend.', 'Lahore', 'DHA', 'football, fitness, cricket', 120),
    ('laiba_plants', 'Laiba Siddiqui', 'Plant mum of 40. Balcony jungle.', 'Lahore', 'Johar Town', 'gardening, plants, baking', 150),
    ('ali_beats', 'Ali Raza', 'Music producer. Lo-fi at 2am.', 'Dubai', 'Marina', 'music, coding, travel', 260),
]

POSTS = {
    'aisha_k': ['Shipped a feature at midnight and celebrated with chai. Worth it.', 'Anyone in Gulberg want to start a weekend coding meetup? ☕', 'Reading the Django docs for fun. Send help.'],
    'bilal_ahmed': ['Nets session this morning. Still can\'t play the pull shot 😅', 'Roadmaps are just opinions with dates attached.', 'Looking for DHA folks for Saturday cricket. All levels welcome!'],
    'sana_codes': ['Dark mode or nothing. Fight me.', 'Finally fixed that flexbox bug. It was one missing min-width.', 'New desk plant, new productivity (probably).'],
    'hamza_lens': ['Golden hour at the old city today.', 'Street photography tip: wait for the moment, not the shot.', 'Shot this on a rainy evening near Liberty.'],
    'mehr_bakes': ['Sourdough number 14. The crumb is finally right!', 'Cardamom cinnamon rolls for the neighbours 🧁', 'Anyone want my starter? I have way too much.'],
    'usman_fit': ['5am run along the sea. Nobody there but me and the gulls.', 'New deadlift PR! Consistency beats motivation.', 'Rest days are part of the plan.'],
    'zara_art': ['Finished this watercolour of my cat. She is not impressed.', 'Sketchbook page: tiny worlds.', 'Illustration challenge day 12: "cozy".'],
    'omar_trails': ['Margalla trail at sunrise. Worth the early alarm.', 'Packing list for the weekend trek: less than you think.', 'Trail run recovery: tea and nothing else.'],
    'hira_reads': ['Book 47 done! Recommendations for the next one?', 'A quiet corner and rain outside. Perfect.', 'Writing a little every day, even when it is bad.'],
    'danish_dev': ['Django tip: select_related saved me 200 queries today.', 'Migrations reviewed, tests green, coffee hot.', 'Anyone else in F-7 working from cafés on Fridays?'],
    'noor_cafe': ['New single-origin beans in. Notes of blueberry and caramel.', 'Latte art attempt #112. Getting there.', 'Our café is hosting an open-mic night on Friday 🎤'],
    'faisal_fc': ['Sunday league: 3-1 win! Proud of the lads.', 'Drills for the week: passing under pressure.', 'Looking for a goalkeeper in DHA, any takers?'],
    'laiba_plants': ['The monstera got a new leaf!', 'Balcony garden update: tomatoes are coming 🍅', 'Propagation station is thriving.'],
    'ali_beats': ['New beat tape dropping this week.', 'Lo-fi, rain sounds and a cup of chai.', 'Dubai marina at night is a mood.'],
}

COMMENTS = ['Love this!', 'Great shot 🔥', 'Totally agree', 'This made my day', 'Count me in!', 'Wow, well done', 'So relatable 😂', 'Where was this taken?', 'Save me a seat next time', 'Brilliant']

PALETTES = [((16, 29, 41), (163, 230, 53)), ((30, 64, 175), (125, 211, 252)), ((190, 24, 93), (253, 186, 116)), ((13, 148, 136), (190, 242, 100)),
            ((88, 28, 135), (244, 114, 182)), ((120, 53, 15), (252, 211, 77)), ((15, 118, 110), (125, 211, 252)), ((127, 29, 29), (252, 165, 165))]


def _gradient(size, top, bottom):
    img = Image.new('RGB', size, top)
    px = ImageDraw.Draw(img)
    for y in range(size[1]):
        t = y / (size[1] - 1)
        px.line([(0, y), (size[0], y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def make_post_image(rng, label):
    top, bottom = rng.choice(PALETTES)
    img = _gradient((960, 640), top, bottom)
    draw = ImageDraw.Draw(img, 'RGBA')
    for _ in range(7):
        r = rng.randint(40, 220)
        x, y = rng.randint(-40, 1000), rng.randint(-40, 680)
        shade = rng.choice([(255, 255, 255, 38), (0, 0, 0, 30), (255, 255, 255, 70)])
        draw.ellipse([x - r, y - r, x + r, y + r], fill=shade)
    try:
        font = ImageFont.load_default(size=44)
    except TypeError:  # very old Pillow
        font = ImageFont.load_default()
    draw.text((48, 560), label, fill=(255, 255, 255, 235), font=font)
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=86)
    return ContentFile(buffer.getvalue())


def make_avatar(name, hue):
    import colorsys
    top = tuple(int(c * 255) for c in colorsys.hls_to_rgb(hue / 360, 0.6, 0.65))
    bottom = tuple(int(c * 255) for c in colorsys.hls_to_rgb(((hue + 40) % 360) / 360, 0.38, 0.65))
    img = _gradient((256, 256), top, bottom)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=130)
    except TypeError:
        font = ImageFont.load_default()
    letter = name[0].upper()
    box = draw.textbbox((0, 0), letter, font=font)
    draw.text(((256 - (box[2] - box[0])) / 2 - box[0], (256 - (box[3] - box[1])) / 2 - box[1]), letter, fill='white', font=font)
    buffer = io.BytesIO()
    img.save(buffer, 'PNG')
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = 'DEMO DATA ONLY: create sample users, posts, likes, comments and follows.'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true', help='Delete the demo users (and their content) before creating them again.')

    def handle(self, *args, **options):
        usernames = [p[0] for p in PEOPLE]
        existing = User.objects.filter(username__in=usernames)
        if existing.exists():
            if not options['reset']:
                self.stdout.write(self.style.WARNING('Demo users already exist. Use --reset to recreate them.'))
                return
            for user in existing:
                if user.profile.avatar:
                    user.profile.avatar.delete(save=False)
                for post in user.posts.exclude(image=''):
                    post.image.delete(save=False)
            existing.delete()

        rng = random.Random(7)
        now = timezone.now()
        users = {}
        for username, full_name, bio, city, hood, interests, hue in PEOPLE:
            user = User.objects.create_user(username=username, password=DEMO_PASSWORD, email=f'{username}@example.com')
            profile = user.profile
            profile.full_name, profile.bio, profile.city, profile.neighbourhood, profile.interests = full_name, bio, city, hood, interests
            profile.avatar.save(f'{username}.png', make_avatar(full_name, hue), save=False)
            profile.save()
            users[username] = user

        all_posts = []
        for username, texts in POSTS.items():
            for i, text in enumerate(texts):
                post = Post(author=users[username], text=text)
                if i != 1 or rng.random() < 0.5:  # roughly two thirds of posts carry a picture
                    post.image.save(f'{username}-{i}.jpg', make_post_image(rng, users[username].profile.display_name), save=False)
                post.save()
                when = now - timedelta(hours=rng.randint(1, 70), minutes=rng.randint(0, 59))
                Post.objects.filter(pk=post.pk).update(created_at=when, updated_at=when)  # keep "edited" off demo posts
                all_posts.append(post)

        names = list(users.values())
        for user in names:
            for other in rng.sample([u for u in names if u != user], 6):
                Follow.objects.get_or_create(follower=user, followee=other)
                notify(other, user, Notification.FOLLOW)
        for post in all_posts:
            for liker in rng.sample([u for u in names if u != post.author], rng.randint(2, 9)):
                _, created = Like.objects.get_or_create(user=liker, post=post)
                if created:
                    notify(post.author, liker, Notification.LIKE, post=post)
            for commenter in rng.sample([u for u in names if u != post.author], rng.randint(0, 3)):
                Comment.objects.create(post=post, author=commenter, text=rng.choice(COMMENTS))
                notify(post.author, commenter, Notification.COMMENT, post=post)

        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} demo users, {len(all_posts)} posts, likes, comments and follows.'))
        self.stdout.write(f'Log in as any of: {", ".join(usernames[:5])}, ...  Password for all demo accounts: {DEMO_PASSWORD}')
