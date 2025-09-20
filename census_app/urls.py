from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="core:home", permanent=False)),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("census_app.core.urls")),
    path("surveys/", include("census_app.surveys.urls")),
    path("api/", include("census_app.api.urls")),
]
