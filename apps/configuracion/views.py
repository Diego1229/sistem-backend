from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Sede, MetodoPago, TipoMovimientoInventario, TipoMovimientoCaja, Impuesto, Caja, Consecutivo
from .serializers import (
    SedeSerializer, MetodoPagoSerializer, TipoMovimientoInvSerializer,
    TipoMovimientoCajaSerializer, ImpuestoSerializer, CajaSerializer, ConsecutivoSerializer
)


def es_admin(user):
    """Verifica si el usuario tiene rol admin en cualquier sede."""
    try:
        from apps.usuarios.models import UsuarioRol
        return UsuarioRol.objects.filter(
            usuario=user,
            rol__nombre='admin',
            activo=True
        ).exists()
    except Exception:
        return False


class SedeViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SedeSerializer

    def get_queryset(self):
        return Sede.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores pueden crear sedes.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'data': serializer.data, 'message': 'Sede creada correctamente.'}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores pueden editar sedes.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores pueden eliminar sedes.'}, status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response({'ok': True, 'message': 'Sede desactivada correctamente.'})


class MetodoPagoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MetodoPagoSerializer
    queryset = MetodoPago.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)


class TipoMovimientoInvViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TipoMovimientoInvSerializer
    queryset = TipoMovimientoInventario.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class TipoMovimientoCajaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TipoMovimientoCajaSerializer
    queryset = TipoMovimientoCaja.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class ImpuestoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ImpuestoSerializer
    queryset = Impuesto.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class CajaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CajaSerializer

    def get_queryset(self):
        return Caja.objects.filter(activo=True).select_related('sede')

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO', 'message': 'Solo administradores pueden crear cajas.'}, status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class ConsecutivoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ConsecutivoSerializer

    def get_queryset(self):
        if not es_admin(self.request.user):
            return Consecutivo.objects.none()
        return Consecutivo.objects.all().select_related('sede')