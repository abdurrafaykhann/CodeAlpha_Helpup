from collections import Counter

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import Profile
from notifications.models import Notification
from notifications.services import notify, retract
from posts.models import Post
from posts.views import is_ajax, safe_redirect

from .models import Follow
from .services import following_ids, shared_interests, suggest_users

User = get_user_model()


@login_required
@require_POST
def follow_toggle(request, username):
    target = get_object_or_404(User, username=username)
    if target == request.user:
        if is_ajax(request):
            return JsonResponse({'error': "You can't follow yourself."}, status=400)
        messages.error(request, "You can't follow yourself.")
        return redirect('accounts:profile', username=username)
    follow, created = Follow.objects.get_or_create(follower=request.user, followee=target)  # no duplicates
    if created:
        notify(target, request.user, Notification.FOLLOW)
    else:
        follow.delete()
        retract(target, request.user, Notification.FOLLOW)
    followers = Follow.objects.filter(followee=target).count()
    if is_ajax(request):
        return JsonResponse({'following': created, 'followers_count': followers})
    return safe_redirect(request, reverse('accounts:profile', args=[username]))


def _user_list(request, profile_user, kind):
    if kind == 'followers':
        rows = Follow.objects.filter(followee=profile_user).select_related('follower', 'follower__profile')
        users = [row.follower for row in rows]
    else:
        rows = Follow.objects.filter(follower=profile_user).select_related('followee', 'followee__profile')
        users = [row.followee for row in rows]
    page = Paginator(users, 20).get_page(request.GET.get('page'))
    return render(request, 'social/user_list.html', {
        'profile_user': profile_user,
        'page': page,
        'kind': kind,
        'followed': following_ids(request.user),
    })


@login_required
def followers_list(request, username):
    return _user_list(request, get_object_or_404(User.objects.select_related('profile'), username=username), 'followers')


@login_required
def following_list(request, username):
    return _user_list(request, get_object_or_404(User.objects.select_related('profile'), username=username), 'following')


@login_required
def explore(request):
    query = request.GET.get('q', '').strip()
    scope = request.GET.get('scope', 'all')
    if scope not in {'all', 'people', 'posts'}:
        scope = 'all'
    followed = following_ids(request.user)
    context = {'q': query, 'scope': scope, 'followed': followed}

    if query:
        if scope in {'all', 'people'}:
            context['people'] = (
                User.objects.select_related('profile')
                .filter(
                    Q(username__icontains=query) | Q(profile__full_name__icontains=query) | Q(profile__bio__icontains=query)
                    | Q(profile__interests__icontains=query) | Q(profile__city__icontains=query)
                )
                .exclude(pk=request.user.pk)
                .distinct()[:24]
            )
        if scope in {'all', 'posts'}:
            context['posts'] = Post.objects.with_stats(request.user).filter(text__icontains=query)[:20]
    else:
        context['suggestions'] = suggest_users(request.user, limit=8)
        context['recent'] = Post.objects.with_stats(request.user)[:9]
    return render(request, 'social/explore.html', context)


def _distinct_locations(values):
    """Case-insensitive distinct values, keeping the first spelling seen."""
    spellings = {}
    for value in values:
        if value:
            spellings.setdefault(value.lower(), Counter())[value] += 1
    # keep the most common spelling, preferring one that is not all lower-case
    best = [max(c, key=lambda v: (c[v], not v.islower())) for c in spellings.values()]
    return sorted(best, key=str.lower)


@login_required
def nearby(request):
    me = request.user.profile
    visible = Profile.objects.filter(show_in_nearby=True).exclude(user=request.user).select_related('user')

    city = request.GET.get('city', me.city if 'city' not in request.GET else '').strip()
    neighbourhood = request.GET.get('neighbourhood', '').strip()
    interest = request.GET.get('interest', '').strip().lower()

    cities = _distinct_locations(visible.exclude(city='').values_list('city', flat=True))
    in_city = visible.filter(city__iexact=city) if city else visible
    neighbourhoods = _distinct_locations(in_city.exclude(neighbourhood='').values_list('neighbourhood', flat=True))
    interests = _distinct_locations(i for p in in_city for i in p.interest_list)

    results = in_city
    if neighbourhood:
        results = results.filter(neighbourhood__iexact=neighbourhood)
    if interest:
        results = results.filter(interests__icontains=interest)
    results = [p for p in results if not interest or interest in p.interest_list or interest in p.interests.lower()]

    my_interests = set(me.interest_list)
    cards = []
    for p in results:
        common = shared_interests(request.user, p)
        same_hood = bool(me.neighbourhood) and p.neighbourhood.lower() == me.neighbourhood.lower()
        cards.append({'profile': p, 'user': p.user, 'shared': common, 'same_neighbourhood': same_hood})
    cards.sort(key=lambda c: (c['same_neighbourhood'], len(c['shared']), c['user'].date_joined), reverse=True)

    return render(request, 'social/nearby.html', {
        'cards': cards[:60],
        'total': len(cards),
        'city': city,
        'neighbourhood': neighbourhood,
        'interest': interest,
        'cities': cities,
        'neighbourhoods': neighbourhoods,
        'interests': interests[:20],
        'followed': following_ids(request.user),
        'my_profile': me,
        'my_interests': my_interests,
    })
