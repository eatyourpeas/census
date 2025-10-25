"""Custom error handler views for Django error pages."""

from django.http import HttpRequest, HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.shortcuts import render


def custom_permission_denied_view(request: HttpRequest, exception=None) -> HttpResponse:
    """Custom 403 error handler."""
    return render(request, "403.html", status=403)


def custom_page_not_found_view(request: HttpRequest, exception=None) -> HttpResponse:
    """Custom 404 error handler."""
    return HttpResponseNotFound(render(request, "404.html").content)


def custom_server_error_view(request: HttpRequest) -> HttpResponse:
    """Custom 500 error handler."""
    return HttpResponseServerError(render(request, "500.html").content)
