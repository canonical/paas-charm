# Copyright 2024 Canonical Ltd.
# See LICENSE file for licensing details.

import time

from django.http import HttpResponse


def sleep(request):
    duration = request.GET.get("duration")
    time.sleep(int(duration))
    return HttpResponse()
