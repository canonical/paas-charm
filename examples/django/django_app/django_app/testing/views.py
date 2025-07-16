# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import json
import os
import time

import urllib3
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from openfga_sdk import ClientConfiguration
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from openfga_sdk.sync import OpenFgaClient
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

from authlib.integrations.django_client import OAuth
from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.shortcuts import redirect
from django.urls import reverse

CONF_URL = f'{os.getenv("DJANGO_OIDC_API_BASE_URL")}/.well-known/openid-configuration'
oauth = OAuth()
oauth.register(
    name="oidc",
    server_metadata_url=CONF_URL,
    client_kwargs={**json.loads(os.getenv("DJANGO_OIDC_CLIENT_KWARGS", "{}")), "verify": False},
)


def profile(request):
    user = request.session.get("user")
    uri = reverse("logout")
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Profile</title>
</head>
<body>
    <h1>Welcome, {user.get('email')}!</h1>
    <p>Here is your user information:</p>
    <pre>{user}</pre>
    <p><a href="/{uri}">Logout</a></p>
</body>
</html>
    
"""
    return HttpResponse(html)


def auth_login(request):
    redirect_uri = request.build_absolute_uri(reverse("callback")).rstrip("/")
    print(f"{redirect_uri=}")
    return oauth.oidc.authorize_redirect(request, redirect_uri)


def callback(request):
    token = oauth.oidc.authorize_access_token(request)
    request.session["user"] = token["userinfo"]
    return redirect(reverse("profile"))


def logout(request):
    request.session.pop("user", None)
    return redirect("/")


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


def list_authorization_models(request):
    try:
        if request.method == "GET":
            configuration = ClientConfiguration(
                api_url=settings.FGA_HTTP_API_URL,
                store_id=settings.FGA_STORE_ID,
                credentials=Credentials(
                    method="api_token",
                    configuration=CredentialConfiguration(api_token=settings.FGA_TOKEN),
                ),
            )
            fga_client = OpenFgaClient(configuration)
            fga_client.read_authorization_models()
            return HttpResponse("Listed authorization models")
    except urllib3.exceptions.HTTPError as e:
        return HttpResponse(f"Failed reaching OpenFGA server: {e}")
    except Exception as e:
        return HttpResponse(f"Failed to list authorization models: {e}")


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
