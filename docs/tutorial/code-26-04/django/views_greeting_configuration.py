import os

from django.http import HttpResponse


def index(request):
    return HttpResponse(f"{os.environ.get('GREETING_VAR', 'Hello, world!')}\n")
