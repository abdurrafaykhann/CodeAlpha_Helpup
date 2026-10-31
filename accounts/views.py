from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from posts.forms import PostForm
from posts.models import Post
from social.models import Follow

from .forms import LoginForm, ProfileForm, RegisterForm

User = get_user_model()


class HelpupLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Welcome to HELPUP, {user.profile.display_name}! Complete your profile to get discovered.')
        return redirect('accounts:profile_edit')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile_detail(request, username):
    profile_user = get_object_or_404(User.objects.select_related('profile'), username=username)
    posts = Post.objects.with_stats(request.user).filter(author=profile_user).order_by('-created_at', '-pk')
    page = Paginator(posts, 8).get_page(request.GET.get('page'))
    context = {
        'profile_user': profile_user,
        'page': page,
        'post_count': page.paginator.count,
        'followers_count': Follow.objects.filter(followee=profile_user).count(),
        'following_count': Follow.objects.filter(follower=profile_user).count(),
        'is_following': Follow.objects.filter(follower=request.user, followee=profile_user).exists(),
        'is_me': profile_user == request.user,
        'form': PostForm() if profile_user == request.user else None,
    }
    return render(request, 'accounts/profile_detail.html', context)


@login_required
def profile_edit(request):
    profile = request.user.profile
    form = ProfileForm(request.POST or None, request.FILES or None, instance=profile)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('accounts:profile', username=request.user.username)
        messages.error(request, 'Please fix the errors below.')
    return render(request, 'accounts/profile_edit.html', {'form': form})
