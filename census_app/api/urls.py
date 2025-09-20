from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'surveys', views.SurveyViewSet, basename='survey')
router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    path('health', views.healthcheck, name='healthcheck'),
    path('', include(router.urls)),
]
