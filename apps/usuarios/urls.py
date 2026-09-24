from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, LogoutView, UsuarioViewSet, RolViewSet

router = DefaultRouter()
# 'roles' debe registrarse ANTES que el prefijo vacío ('') de UsuarioViewSet.
# De lo contrario, la ruta de detalle de UsuarioViewSet (^(?P<pk>...)/$)
# intercepta '/usuarios/roles/' interpretando 'roles' como un pk, y
# RolViewSet nunca llega a resolverse.
router.register(r'roles', RolViewSet, basename='roles')
router.register(r'', UsuarioViewSet, basename='usuarios')

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
] + router.urls