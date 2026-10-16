import os

from django.http import HttpResponse


def index(request):
    return HttpResponse(os.environ.get("GREETING_VAR", "Hello, world!"), content_type="text/plain")
