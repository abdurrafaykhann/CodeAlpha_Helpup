from django.http import JsonResponse
from django.shortcuts import render


def permission_denied(request, exception=None):
    """403 page (or JSON for fetch requests) with a clear message."""
    message = str(exception) if exception and str(exception) else "You don't have permission to do that."
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': message}, status=403)
    return render(request, '403.html', {'message': message}, status=403)
