from django.shortcuts import render

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Categoria, Producto, Inventario, Movimiento, Lote
from .serializers import (
    CategoriaSerializer, ProductoListSerializer, ProductoDetailSerializer,
    InventarioSerializer, MovimientoSerializer, AjusteStockSerializer, LoteSerializer
)
from .services import ajustar_stock
from apps.usuarios.permissions import es_admin, get_sede_activa


class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CategoriaSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre']

    def get_queryset(self):
        return Categoria.objects.filter(activo=True)

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear categorías.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'data': serializer.data,
            'message': 'Categoría creada.'}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden editar categorías.'},
                status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden desactivar categorías.'},
                status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response({'ok': True, 'message': 'Categoría desactivada.'})


class ProductoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, OrderingFilter, DjangoFilterBackend]
    search_fields = ['nombre', 'codigo_barras', 'sku']
    ordering_fields = ['nombre', 'precio_venta', 'fecha_creacion']
    filterset_fields = ['activo', 'controla_stock']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoDetailSerializer

    def get_queryset(self):
        return Producto.objects.filter(activo=True).select_related(
            'impuesto'
        ).prefetch_related('categorias__categoria')

    def create(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden crear productos.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        return Response({'ok': True, 'data': ProductoDetailSerializer(producto).data,
            'message': 'Producto creado correctamente.'}, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden editar productos.'},
                status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'ok': True, 'data': serializer.data, 'message': 'Producto actualizado.'})

    def destroy(self, request, *args, **kwargs):
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden desactivar productos.'},
                status=status.HTTP_403_FORBIDDEN)
        instance = self.get_object()
        instance.activo = False
        instance.fecha_actualizacion = timezone.now()
        instance.save()
        return Response({'ok': True, 'message': 'Producto desactivado.'})

    @action(detail=False, methods=['post'], url_path='ajuste-stock')
    def ajuste_stock(self, request):
        """POST /api/v1/inventario/productos/ajuste-stock/ — solo admin."""
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden hacer ajustes de stock.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = AjusteStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            movimiento, stock_nuevo = ajustar_stock(
                producto_id=d['producto_id'],
                sede_id=d['sede_id'],
                cantidad=d['cantidad'],
                tipo_movimiento_id=d['tipo_movimiento_id'],
                usuario=request.user,
                observacion=d.get('observacion', '')
            )
            return Response({'ok': True,
                'message': f'Stock ajustado. Nuevo stock: {stock_nuevo}'})
        except ValueError as e:
            return Response({'ok': False, 'error': 'STOCK_ERROR',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class InventarioViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = InventarioSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    search_fields = ['producto__nombre', 'producto__sku']
    filterset_fields = ['sede']

    def get_queryset(self):
        qs = Inventario.objects.select_related('producto', 'sede')
        if es_admin(self.request.user):
            return qs
        # Vendedor solo ve stock de su sede
        sede = get_sede_activa(self.request.user)
        if sede:
            return qs.filter(sede=sede)
        return Inventario.objects.none()


class MovimientoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MovimientoSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['sede', 'producto', 'tipo_movimiento']
    ordering_fields = ['fecha_movimiento']

    def get_queryset(self):
        qs = Movimiento.objects.select_related(
            'producto', 'sede', 'tipo_movimiento', 'usuario'
        )
        if es_admin(self.request.user):
            return qs
        sede = get_sede_activa(self.request.user)
        if sede:
            return qs.filter(sede=sede)
        return Movimiento.objects.none()


class LoteViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LoteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['sede', 'producto', 'activo']

    def get_queryset(self):
        return Lote.objects.filter(activo=True).select_related('producto', 'sede')