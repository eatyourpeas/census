from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("home", views.home, name="home"),
    path("profile", views.profile, name="profile"),
    path("signup/", views.signup, name="signup"),
]
