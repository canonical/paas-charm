from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world!", content_type="text/plain")
