from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

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
    path('', include(router.urls)),
]
