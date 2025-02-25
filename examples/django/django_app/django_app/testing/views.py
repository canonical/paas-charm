# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import time

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def environ(request):
    return JsonResponse(dict(os.environ))


def user_count(request):
    return JsonResponse(User.objects.count(), safe=False)


def get_settings(request, name):
    if hasattr(settings, name):
        return JsonResponse(getattr(settings, name), safe=False)
    else:
        return JsonResponse({"error": f"settings {name!r} not found"}, status=404)


def hello_world(request):
    # Create a custom span
    with tracer.start_as_current_span("custom-span"):
        print("Hello, World!!!")
    return HttpResponse("Hello, World!")


def sleep(request):
    duration = request.GET.get("duration")
    time.sleep(int(duration))
    return HttpResponse()


def login(request):
    user = authenticate(username=request.GET.get("username"), password=request.GET.get("password"))
    if user is not None:
        return HttpResponse(status=200)
    else:
        return HttpResponse(status=403)
