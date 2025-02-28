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

from django.conf import settings
from django.core.mail import EmailMessage, get_connection


def send_mail(request):
    try:
        if request.method == "GET":
            with get_connection(
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=(
                    settings.EMAIL_HOST_USER
                    if settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL
                    else None
                ),
                password=(
                    settings.EMAIL_HOST_PASSWORD
                    if settings.EMAIL_USE_TLS or settings.EMAIL_USE_SSL
                    else None
                ),
                use_tls=settings.EMAIL_USE_TLS,
            ) as connection:
                subject = "hello"
                email_from = "tester@example.com"
                recipient_list = ["test@example.com"]
                message = "Hello world!"
                EmailMessage(
                    subject, message, email_from, recipient_list, connection=connection
                ).send()

        return HttpResponse("Sent")
    except Exception as e:
        return HttpResponse(f"Failed to send information: {e}")


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
