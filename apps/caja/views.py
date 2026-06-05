from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from .models import Apertura, MovimientoCaja, CierreCaja
from .serializers import (
    AperturaSerializer, AbrirCajaSerializer, MovimientoCajaSerializer,
    RegistrarMovimientoSerializer, CierreCajaSerializer, CerrarCajaSerializer
)
from .services import abrir_caja, cerrar_caja, get_apertura_activa
from apps.usuarios.permissions import es_admin, get_sede_activa
from apps.configuracion.models import TipoMovimientoCaja


class AperturaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AperturaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['estado', 'sede', 'caja']
    ordering_fields = ['fecha_apertura']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = Apertura.objects.select_related('sede', 'caja', 'usuario')
        if es_admin(self.request.user):
            return qs
        # Vendedor solo ve sus propias aperturas
        return qs.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        """POST /api/v1/caja/aperturas/ — abrir turno."""
        serializer = AbrirCajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        sede = get_sede_activa(request.user)
        if not sede:
            return Response({'ok': False, 'error': 'SIN_SEDE',
                'message': 'El usuario no tiene sede asignada.'},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            apertura = abrir_caja(
                caja_id=d['caja_id'],
                sede_id=sede.id,
                usuario=request.user,
                monto_inicial=d.get('monto_inicial', 0),
                observacion=d.get('observacion', '')
            )
            return Response({'ok': True,
                'data': AperturaSerializer(apertura).data,
                'message': 'Caja abierta correctamente.'
            }, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_APERTURA',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """POST /api/v1/caja/aperturas/{id}/cerrar/"""
        apertura = self.get_object()

        # Vendedor solo puede cerrar su propio turno
        if not es_admin(request.user) and apertura.usuario != request.user:
            return Response({'ok': False, 'error': 'PERMISO_DENEGADO',
                'message': 'Solo puede cerrar su propio turno.'},
                status=status.HTTP_403_FORBIDDEN)

        serializer = CerrarCajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        try:
            cierre = cerrar_caja(
                apertura_id=pk,
                usuario=request.user,
                total_real=d['total_real'],
                observacion=d.get('observacion', ''),
                desgloses=d.get('desgloses', [])
            )
            return Response({'ok': True,
                'data': CierreCajaSerializer(cierre).data,
                'message': f'Caja cerrada. Diferencia: ${cierre.diferencia}'
            })
        except ValueError as e:
            return Response({'ok': False, 'error': 'ERROR_CIERRE',
                'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='activa')
    def activa(self, request):
        """GET /api/v1/caja/aperturas/activa/ — apertura activa del usuario."""
        sede = get_sede_activa(request.user)
        apertura = get_apertura_activa(
            sede_id=sede.id if sede else None,
            usuario=request.user if not es_admin(request.user) else None
        )
        if not apertura:
            return Response({'ok': False, 'error': 'SIN_APERTURA',
                'message': 'No hay caja abierta.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'ok': True, 'data': AperturaSerializer(apertura).data})


class MovimientoCajaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MovimientoCajaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['tipo', 'apertura']
    ordering_fields = ['fecha_movimiento']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        qs = MovimientoCaja.objects.select_related(
            'caja', 'apertura', 'usuario', 'tipo_movimiento_caja'
        )
        if es_admin(self.request.user):
            return qs
        return qs.filter(usuario=self.request.user)

    def create(self, request, *args, **kwargs):
        """Registra un movimiento manual en la caja activa."""
        serializer = RegistrarMovimientoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data

        sede = get_sede_activa(request.user)
        apertura = get_apertura_activa(
            sede_id=sede.id if sede else None,
            usuario=request.user if not es_admin(request.user) else None
        )
        if not apertura:
            return Response({'ok': False, 'error': 'SIN_APERTURA',
                'message': 'No hay caja abierta para registrar movimientos.'},
                status=status.HTTP_400_BAD_REQUEST)

        tipo_mov = TipoMovimientoCaja.objects.get(pk=d['tipo_movimiento_caja_id'])

        movimiento = MovimientoCaja.objects.create(
            caja=apertura.caja,
            apertura=apertura,
            usuario=request.user,
            tipo_movimiento_caja=tipo_mov,
            monto=d['monto'],
            tipo=tipo_mov.tipo,
            concepto=d['concepto']
        )
        return Response({'ok': True,
            'data': MovimientoCajaSerializer(movimiento).data,
            'message': 'Movimiento registrado.'
        }, status=status.HTTP_201_CREATED)


class CierreCajaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CierreCajaSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['fecha_cierre']

    def get_queryset(self):
        qs = CierreCaja.objects.select_related(
            'apertura', 'usuario_cierre'
        ).prefetch_related('desgloses__metodo_pago')
        if es_admin(self.request.user):
            return qs
        return qs.filter(apertura__usuario=self.request.user)