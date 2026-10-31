from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    qs = Notification.objects.filter(recipient=request.user).select_related('actor', 'actor__profile', 'post')
    page = Paginator(qs, 25).get_page(request.GET.get('page'))
    unread_ids = [n.pk for n in page if not n.is_read]
    response = render(request, 'notifications/list.html', {'page': page, 'unread_ids': unread_ids})
    # Opening the page marks what was shown as read (the template still highlights the new ones).
    Notification.objects.filter(pk__in=unread_ids).update(is_read=True)
    return response


@login_required
@require_POST
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect('notifications:list')


@login_required
def unread_count(request):
    return JsonResponse({'count': Notification.objects.filter(recipient=request.user, is_read=False).count()})
