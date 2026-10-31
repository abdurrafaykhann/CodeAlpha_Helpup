from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from notifications.models import Notification
from notifications.services import notify, retract
from social.models import Follow
from social.services import recommended_posts, suggest_users

from .forms import CommentForm, PostForm
from .models import Comment, Like, Post


def is_ajax(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def safe_redirect(request, fallback):
    target = request.POST.get('next') or request.META.get('HTTP_REFERER') or fallback
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback)


def home(request):
    if not request.user.is_authenticated:
        return render(request, 'landing.html')

    tab = 'latest' if request.GET.get('tab') == 'latest' else 'following'
    posts = Post.objects.with_stats(request.user)
    if tab == 'following':
        followed = list(Follow.objects.filter(follower=request.user).values_list('followee_id', flat=True))
        posts = posts.filter(author_id__in=followed + [request.user.id])
    page = Paginator(posts.order_by('-created_at', '-pk'), 8).get_page(request.GET.get('page'))

    # A thin "following" feed is topped up with recommendations so it never feels empty.
    recommended = []
    if tab == 'following' and page.number == 1 and page.paginator.count < 6:
        recommended = recommended_posts(request.user, exclude_ids=[p.pk for p in page], limit=6)

    return render(request, 'posts/home.html', {
        'form': PostForm(),
        'page': page,
        'tab': tab,
        'recommended': recommended,
        'suggestions': suggest_users(request.user, limit=5),
    })


@login_required
def post_create(request):
    form = PostForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        messages.success(request, 'Your post is live.')
        return redirect('home')
    if request.method == 'POST':
        messages.error(request, 'Your post could not be published. Please fix the errors below.')
    return render(request, 'posts/post_form.html', {'form': form, 'editing': False})


def get_owned_post(request, pk):
    post = get_object_or_404(Post, pk=pk)
    if post.author_id != request.user.id:
        raise PermissionDenied('You can only change your own posts.')
    return post


@login_required
def post_edit(request, pk):
    post = get_owned_post(request, pk)
    form = PostForm(request.POST or None, request.FILES or None, instance=post)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated.')
            return redirect(post)
        messages.error(request, 'Your changes could not be saved. Please fix the errors below.')
    return render(request, 'posts/post_form.html', {'form': form, 'editing': True, 'post': post})


@login_required
def post_delete(request, pk):
    post = get_owned_post(request, pk)
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted.')
        return redirect('accounts:profile', username=request.user.username)
    return render(request, 'posts/post_confirm_delete.html', {'post': post})


@login_required
def post_detail(request, pk):
    get_object_or_404(Post, pk=pk)
    post = Post.objects.with_stats(request.user).get(pk=pk)
    comments = post.comments.select_related('author', 'author__profile')
    return render(request, 'posts/post_detail.html', {'post': post, 'comments': comments, 'comment_form': CommentForm()})


@login_required
@require_POST
def like_toggle(request, pk):
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(user=request.user, post=post)  # unique constraint prevents duplicates
    if created:
        notify(post.author, request.user, Notification.LIKE, post=post)
    else:
        like.delete()
        retract(post.author, request.user, Notification.LIKE, post=post)
    count = post.likes.count()
    if is_ajax(request):
        return JsonResponse({'liked': created, 'count': count})
    return safe_redirect(request, reverse('posts:detail', args=[pk]))


@login_required
def comment_list(request, pk):
    post = get_object_or_404(Post, pk=pk)
    comments = post.comments.select_related('author', 'author__profile')
    html = render_to_string('partials/comment_list.html', {'comments': comments}, request=request)
    return JsonResponse({'html': html, 'count': comments.count()})


@login_required
@require_POST
def comment_add(request, pk):
    post = get_object_or_404(Post, pk=pk)
    form = CommentForm(request.POST)
    if not form.is_valid():
        error = form.errors['text'][0] if 'text' in form.errors else 'Invalid comment.'
        if is_ajax(request):
            return JsonResponse({'error': error}, status=400)
        messages.error(request, error)
        return redirect('posts:detail', pk=pk)
    comment = form.save(commit=False)
    comment.post, comment.author = post, request.user
    comment.save()
    notify(post.author, request.user, Notification.COMMENT, post=post)
    if is_ajax(request):
        html = render_to_string('partials/comment.html', {'comment': comment}, request=request)
        return JsonResponse({'html': html, 'count': post.comments.count()}, status=201)
    return redirect(reverse('posts:detail', args=[pk]) + '#comments')


@login_required
@require_POST
def comment_delete(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    if comment.author_id != request.user.id:
        raise PermissionDenied('You can only delete your own comments.')
    post = comment.post
    comment.delete()
    if is_ajax(request):
        return JsonResponse({'count': post.comments.count()})
    messages.success(request, 'Comment deleted.')
    return redirect(reverse('posts:detail', args=[post.pk]) + '#comments')
