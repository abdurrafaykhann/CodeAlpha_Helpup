"""Recommendation helpers shared by the feed, Explore and Nearby pages."""
from django.contrib.auth import get_user_model
from django.db.models import Count

from posts.models import Post

from .models import Follow

User = get_user_model()


def following_ids(user):
    return set(Follow.objects.filter(follower=user).values_list('followee_id', flat=True))


def _score(me, other_profile):
    """Higher = more relevant. Uses only city, neighbourhood and shared interests."""
    mine = me.profile
    score = 0
    if mine.city and other_profile.city.lower() == mine.city.lower():
        score += 3
        if mine.neighbourhood and other_profile.neighbourhood.lower() == mine.neighbourhood.lower():
            score += 2
    score += 2 * len(set(mine.interest_list) & set(other_profile.interest_list))
    return score


def shared_interests(me, other_profile):
    return sorted(set(me.profile.interest_list) & set(other_profile.interest_list))


def suggest_users(user, limit=8):
    """People you don't follow yet, ranked by closeness and then popularity."""
    followed = following_ids(user)
    candidates = (
        User.objects.exclude(pk__in=followed | {user.pk})
        .select_related('profile')
        .annotate(follower_total=Count('followers_set'))
        .order_by('-follower_total', '-date_joined')[:60]
    )
    ranked = sorted(candidates, key=lambda c: (_score(user, c.profile), c.follower_total), reverse=True)
    return ranked[:limit]


def recommended_posts(user, exclude_ids=(), limit=6):
    """Recent posts from people you don't follow, favouring your city and interests."""
    followed = following_ids(user)
    recent = list(
        Post.objects.with_stats(user)
        .exclude(author_id__in=followed | {user.pk})
        .exclude(pk__in=list(exclude_ids))
        .order_by('-created_at')[:40]
    )
    recent.sort(key=lambda p: _score(user, p.author.profile), reverse=True)  # stable: newest first among equals
    return recent[:limit]
