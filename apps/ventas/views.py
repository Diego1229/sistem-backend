from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Cliente, Venta, FacturaVenta, DevolucionVenta
from .serializers import (
    ClienteSerializer, VentaListSerializer, VentaDetailSerializer,
    CrearVentaSerializer, AnularVentaSerializer,
    FacturaVentaSerializer, DevolucionVentaSerializer,
    CrearDevolucionVentaSerializer
)
from .services import crear_venta, anular_venta, crear_devolucion_venta, aprobar_devolucion_venta
from apps.usuarios.permissions import es_admin, get_sede_activa


class ClienteViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ClienteSerializer
    filter_backends = [SearchFilter]
    search_fields = ['nombre', 'numero_documento', 'telefono']

    def get_queryset(self):
        return Cliente.objects.filter(activo=True)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.activo = False
        instance.save()
        return Response({'ok': True, 'message': 'Cliente desactivado.'})


class VentaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'sede']
    search_fields = ['numero_venta', 'nombre_cliente']
    ordering_fields = ['fecha_venta', 'total']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_serializer_class(self):
        if self.action == 'list':
            return VentaListSerializer
        if self.action == 'create':
            return CrearVentaSerializer
        return VentaDetailSerializer

    def get_queryset(self):
        qs = Venta.objects.select_related(
            'sede', 'usuario', 'apertura_caja', 'caja', 'cliente'
        ).prefetch_related('detalles__producto', 'pagos__metodo_pago')

        if es_admin(self.request.user):
            return qs
        # Vendedor solo ve sus propias ventas
        sede = get_sede_activa(self.request.user)
        return qs.filter(
            usuario=self.request.user,
            sede=sede
        ) if sede else Venta.objects.none()

    def create(self, request, *args, **kwargs):
        """POST /api/v1/ventas/ — crear venta completa."""
        serializer = CrearVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        sede = get_sede_activa(request.user)
        if not sede and not es_admin(request.user):
            return Response({'ok': False, 'error': 'SIN_SEDE',
                'message': 'El usuario no tiene sede asignada.'},
                status=status.HTTP_400_BAD_REQUEST)

        # Admin puede especificar sede, vendedor usa la suya
        sede_id = request.data.get('sede_id') if es_admin(request.user) else sede.id

        try:
            venta = crear_venta(
                usuario=request.user,
                sede_id=sede_id,
                items=d['items'],
                pagos=d['pagos'],
                descuento=d.get('descuento', 0),
                nombre_cliente=d.get('nombre_cliente', ''),
                cliente_id=d.get('cliente_id'),
                observacion=d.get('observacion', '')
            )
            return Response({'ok': True,
                'data': VentaDetailSerializer(venta).data,
                'message': f'Venta {venta.numero_venta} creada exitosamente.'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_VENTA',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='anular')
    def anular(self, request, pk=None):
        """POST /api/v1/ventas/{id}/anular/ — solo admin."""
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden anular ventas.'},
                status=status.HTTP_403_FORBIDDEN)
        serializer = AnularVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            venta = anular_venta(
                venta_id=pk,
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )
            return Response({'ok': True,
                'data': VentaDetailSerializer(venta).data,
                'message': f'Venta {venta.numero_venta} anulada.'
            })
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_ANULACION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get', 'post'], url_path='factura')
    def factura(self, request, pk=None):
        """GET o POST /api/v1/ventas/{id}/factura/"""
        venta = self.get_object()
        if request.method == 'GET':
            try:
                factura = venta.factura
                return Response({'ok': True, 'data': FacturaVentaSerializer(factura).data})
            except FacturaVenta.DoesNotExist:
                return Response({'ok': False, 'error': 'SIN_FACTURA',
                    'message': 'Esta venta no tiene factura generada.'},
                    status=status.HTTP_404_NOT_FOUND)
        # POST — generar factura
        if hasattr(venta, 'factura'):
            return Response({'ok': False, 'error': 'FACTURA_EXISTENTE',
                'message': 'Esta venta ya tiene factura.'},
                status=status.HTTP_400_BAD_REQUEST)
        numero_factura = f"FAC-{venta.numero_venta}"
        factura = FacturaVenta.objects.create(
            venta=venta,
            sede=venta.sede,
            numero_factura=numero_factura,
            nombre_cliente=venta.nombre_cliente,
            subtotal=venta.total,
            total_iva=0,
            total=venta.total,
            estado='emitida'
        )
        return Response({'ok': True,
            'data': FacturaVentaSerializer(factura).data,
            'message': 'Factura generada.'
        }, status=status.HTTP_201_CREATED)


class DevolucionVentaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DevolucionVentaSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['estado']

    def get_queryset(self):
        qs = DevolucionVenta.objects.select_related('venta', 'usuario')
        if es_admin(self.request.user):
            return qs
        return qs.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        POST /api/v1/ventas/devoluciones/
        Registra la devolución en estado 'pendiente' junto con sus líneas
        de detalle. El stock solo se devuelve al aprobar (ver `aprobar`).
        """
        serializer = CrearDevolucionVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            devolucion = crear_devolucion_venta(
                venta_id=d['venta_id'],
                usuario=request.user,
                motivo=d['motivo'],
                detalles=d['detalles']
            )
            return Response({'ok': True,
                'data': DevolucionVentaSerializer(devolucion).data,
                'message': 'Devolución registrada. Pendiente de aprobación.'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_DEVOLUCION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='aprobar')
    def aprobar(self, request, pk=None):
        """
        POST /api/v1/ventas/devoluciones/{id}/aprobar/
        Aprueba la devolución y devuelve el stock de cada producto devuelto.
        """
        if not es_admin(request.user):
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo administradores pueden aprobar devoluciones.'},
                status=status.HTTP_403_FORBIDDEN)
        try:
            devolucion = aprobar_devolucion_venta(
                devolucion_id=pk,
                usuario=request.user
            )
            return Response({'ok': True,
                'data': DevolucionVentaSerializer(devolucion).data,
                'message': 'Devolución aprobada. Stock actualizado.'
            })
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_APROBACION',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
