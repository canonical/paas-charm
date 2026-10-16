# Copyright 2026 Canonical Ltd.
# See LICENSE file for licensing details.

"""URL configuration for the initial greeting."""

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.urls import path


def index(request: HttpRequest) -> HttpResponse:
    """Return the initial greeting.

    Args:
        request: The incoming request.

    Returns:
        The greeting response.
    """
    return HttpResponse("Hello world!")


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
]
