from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from rest_framework.schemas import get_schema_view
from rest_framework.permissions import AllowAny
from django.views.generic import TemplateView

router = DefaultRouter()
router.register(r'surveys', views.SurveyViewSet, basename='survey')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'org-memberships', views.OrganizationMembershipViewSet, basename='org-membership')
router.register(r'survey-memberships', views.SurveyMembershipViewSet, basename='survey-membership')
router.register(r'scoped-users', views.ScopedUserViewSet, basename='scoped-user')

urlpatterns = [
    path('health', views.healthcheck, name='healthcheck'),
    path('token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    # OpenAPI schema (JSON)
    path('schema', get_schema_view(
        title="Census API",
        description="OpenAPI schema for the Census API",
        version="1.0.0",
        permission_classes=[AllowAny],
    ), name='openapi-schema'),
    # Embedded Swagger UI (CSP exempt)
    path('docs', views.swagger_ui, name='swagger-ui'),
    # Embedded ReDoc UI (CSP exempt)
    path('redoc', views.redoc_ui, name='redoc-ui'),
    path('', include(router.urls)),
]
