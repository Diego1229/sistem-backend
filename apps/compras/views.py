from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Proveedor, Compra, FacturaAbastecimiento, DevolucionCompra
from .serializers import (
    ProveedorSerializer, CompraListSerializer, CompraDetailSerializer,
    CrearCompraSerializer, RecibirCompraSerializer,
    FacturaAbastecimientoSerializer, DevolucionCompraSerializer,
    CrearDevolucionCompraSerializer
)
from .services import crear_compra, recibir_compra, crear_devolucion_compra, aprobar_devolucion_compra
from apps.usuarios.permissions import es_admin, get_sede_activa


class ProveedorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProveedorSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'nit']

    def get_queryset(self):
        return Proveedor.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear proveedores.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'data': serializer.data,
            'message': 'Proveedor creado.'}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden editar proveedores.'},
                status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden desactivar proveedores.'},
                status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response({'ok': True, 'message': 'Proveedor desactivado.'})


class CompraViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['estado', 'sede', 'proveedor']
    ordering_fields = ['fecha_compra', 'total']

    def get_serializer_class(self):
        if self.action == 'list':
            return CompraListSerializer
        if self.action == 'create':
            return CrearCompraSerializer
        return CompraDetailSerializer

    def get_queryset(self):
        qs = Compra.objects.select_related(
            'proveedor', 'sede', 'usuario'
        )
        if es_admin(self.request.user):
            return qs
        sede = get_sede_activa(self.request.user)
        return qs.filter(sede=sede) if sede else Compra.objects.none()

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear órdenes de compra.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = CrearCompraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            compra = crear_compra(
                proveedor_id=d['proveedor_id'],
                sede_id=d['sede_id'],
                usuario=request.user,
                no_factura_proveedor=d.get('no_factura_proveedor', ''),
                observacion=d.get('observacion', ''),
                detalles=d['detalles']
            )
            return Response({'ok': True,
                'data': CompraDetailSerializer(compra).data,
                'message': f'Compra {compra.numero_compra} creada.'
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'ok': False, 'error': 'ERROR_COMPRA',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden anular compras.'},
                status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        if instance.estado == 'recibida':
            return Response({'ok': False, 'error': 'COMPRA_RECIBIDA',
                'message': 'No se puede anular una compra ya recibida.'},
                status=status.HTTP_400_BAD_REQUEST)
        instance.estado = 'anulada'
        instance.save()
        return Response({'ok': True, 'message': 'Compra anulada.'})

    @action(detail=True, methods=['post'], url_path='recibir')
    def recibir(self, request, pk=None):
        """
        POST /api/v1/compras/{id}/recibir/
        Recibe la mercancía y actualiza el stock automáticamente.
        Admin y vendedor pueden recibir.
        """
        serializer = RecibirCompraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            compra = recibir_compra(
                compra_id=pk,
                usuario=request.user,
                observacion=serializer.validated_data.get('observacion', '')
            )
            return Response({'ok': True,
                'data': CompraDetailSerializer(compra).data,
                'message': f'Compra {compra.numero_compra} recibida. Stock actualizado.'
            })
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_RECEPCION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class FacturaAbastecimientoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FacturaAbastecimientoSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sede', 'estado']

    def get_queryset(self):
        qs = FacturaAbastecimiento.objects.select_related('proveedor', 'sede', 'compra')
        if es_admin(self.request.user):
            return qs
        sede = get_sede_activa(self.request.user)
        return qs.filter(sede=sede) if sede else FacturaAbastecimiento.objects.none()


class DevolucionCompraViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DevolucionCompraSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado']

    def get_queryset(self):
        return DevolucionCompra.objects.select_related('compra', 'usuario')

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/compras/devoluciones/
        Registra la devolución en estado 'pendiente' junto con sus líneas
        de detalle. El stock solo se descuenta al aprobar (ver `aprobar`).
        """
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear devoluciones.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = CrearDevolucionCompraSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            devolucion = crear_devolucion_compra(
                compra_id=d['compra_id'],
                usuario=request.user,
                motivo=d['motivo'],
                detalles=d['detalles']
            )
            return Response({'ok': True,
                'data': DevolucionCompraSerializer(devolucion).data,
                'message': 'Devolución registrada. Pendiente de aprobación.'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_DEVOLUCION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """
        POST /api/v1/compras/devoluciones/{id}/aprobar/
        Aprueba la devolución y descuenta el stock de cada producto devuelto.
        """
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden aprobar devoluciones.'},
                status=status.HTTP_403_FORBIDDEN)
        try:
            devolucion = aprobar_devolucion_compra(
                devolucion_id=pk,
                usuario=request.user
            )
            return Response({'ok': True,
                'data': DevolucionCompraSerializer(devolucion).data,
                'message': 'Devolución aprobada. Stock actualizado.'
            })
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_APROBACION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

