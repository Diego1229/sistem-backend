from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, UsuarioViewSet, RolViewSet

router = DefaultRouter()
router.register(r'', UsuarioViewSet, basename='usuarios')
router.register(r'roles', RolViewSet, basename='roles')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
] + router.urls