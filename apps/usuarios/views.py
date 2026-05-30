from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Usuario, Rol, UsuarioRol
from .serializers import (
    UsuarioListSerializer, UsuarioDetailSerializer,
    CambiarPasswordSerializer, AsignarRolSerializer, RolSerializer
)
from .permissions import EsAdmin, es_admin
from .services import registrar_acceso, cerrar_sesion_activa


class LoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/login/
    Retorna access + refresh token. Registra el acceso en aud_accesos.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            from .models import Usuario
            nombre_usuario = request.data.get('username') or request.data.get('nombre_usuario')
            try:
                usuario = Usuario.objects.get(nombre_usuario=nombre_usuario)
                registrar_acceso(usuario, 'login', request)
            except Usuario.DoesNotExist:
                pass
            return Response({
                'ok': True,
                'data': response.data,
                'message': 'Login exitoso.'
            })
        return Response({
            'ok': False,
            'error': 'CREDENCIALES_INVALIDAS',
            'message': 'Usuario o contraseña incorrectos.'
        }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(TokenObtainPairView):
    """
    POST /api/v1/auth/logout/
    Invalida el refresh token y registra el logout.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            cerrar_sesion_activa(request.user)
            return Response({'ok': True, 'message': 'Sesión cerrada correctamente.'})
        except Exception:
            return Response({'ok': True, 'message': 'Sesión cerrada.'})


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    /api/v1/usuarios/
    Admin: CRUD completo.
    Vendedor: solo puede ver y editar su propio perfil.
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return UsuarioListSerializer
        return UsuarioDetailSerializer

    def get_queryset(self):
        if es_admin(self.request.user):
            return Usuario.objects.filter(activo=True).prefetch_related('roles__rol', 'roles__sede')
        return Usuario.objects.filter(pk=self.request.user.pk)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({
                'ok': False,
                'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear usuarios.'
            }, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        return Response({
            'ok': True,
            'data': UsuarioDetailSerializer(usuario).data,
            'message': 'Usuario creado correctamente.'
        }, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        # Vendedor solo puede editar su propio perfil
        if not es_admin(request.user) and instance.pk != request.user.pk:
            return Response({
                'ok': False,
                'error': 'PERMISO_DENEGADO',
                'message': 'Solo puede editar su propio perfil.'
            }, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'data': serializer.data, 'message': 'Usuario actualizado.'})

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({
                'ok': False,
                'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden desactivar usuarios.'
            }, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.activo = False
        instance.fecha_actualizacion = timezone.now()
        instance.save()
        return Response({'ok': True, 'message': 'Usuario desactivado correctamente.'})

    @action(detail=False, methods=['get'], url_path='me')
    def me(self, request):
        """GET /api/v1/usuarios/me/ — perfil del usuario autenticado."""
        serializer = UsuarioDetailSerializer(request.user)
        return Response({'ok': True, 'data': serializer.data})

    @action(detail=False, methods=['post'], url_path='me/cambiar-password')
    def cambiar_password(self, request):
        """POST /api/v1/usuarios/me/cambiar-password/"""
        serializer = CambiarPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['password_actual']):
            return Response({
                'ok': False,
                'error': 'PASSWORD_INCORRECTO',
                'message': 'La contraseña actual no es correcta.'
            }, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data['password_nuevo'])
        request.user.fecha_actualizacion = timezone.now()
        request.user.save()
        return Response({'ok': True, 'message': 'Contraseña actualizada correctamente.'})

    @action(detail=True, methods=['post'], url_path='asignar-rol',
            permission_classes=[IsAuthenticated, EsAdmin])
    def asignar_rol(self, request, pk=None):
        """POST /api/v1/usuarios/{id}/asignar-rol/ — solo admin."""
        usuario = self.get_object()
        serializer = AsignarRolSerializer(data={
            'usuario': usuario.pk,
            'rol': request.data.get('rol'),
            'sede': request.data.get('sede'),
        })
        serializer.is_valid(raise_exception=True)

        # Desactivar rol anterior en esa sede si existe
        UsuarioRol.objects.filter(
            usuario=usuario,
            sede_id=request.data.get('sede'),
            activo=True
        ).update(activo=False, fecha_fin=timezone.now())

        ur = serializer.save()
        return Response({
            'ok': True,
            'data': AsignarRolSerializer(ur).data,
            'message': 'Rol asignado correctamente.'
        }, status=status.HTTP_201_CREATED)


class RolViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/v1/usuarios/roles/ — lista de roles disponibles."""
    permission_classes = [IsAuthenticated, EsAdmin]
    serializer_class = RolSerializer
    queryset = Rol.objects.filter(activo=True)