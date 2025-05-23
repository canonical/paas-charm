# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

"""
URL configuration for django_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from testing.views import (
    environ,
    get_settings,
    hello_world,
    list_authorization_models,
    login,
    send_mail,
    sleep,
    user_count,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("settings/<str:name>", get_settings, name="get_settings"),
    path("len/users", user_count, name="user_count"),
    path("environ", environ, name="environ"),
    path("", hello_world, name="hello_world"),
    path("sleep", sleep, name="sleep"),
    path("send_mail", send_mail, name="send_mail"),
    path(
        "openfga/list-authorization-models",
        list_authorization_models,
        name="list_authorization_models",
    ),
    path("login", login, name="login"),
]
