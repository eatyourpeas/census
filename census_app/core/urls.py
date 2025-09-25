from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("home", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    path("profile", views.profile, name="profile"),
    path("signup/", views.signup, name="signup"),
    path("docs/", views.docs_index, name="docs_index"),
    path("docs/<slug:slug>/", views.docs_page, name="docs_page"),
]
