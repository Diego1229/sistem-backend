from rest_framework import serializers
from .models import Apertura, MovimientoCaja, CierreCaja, CierreDesglose


class AperturaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    caja_nombre = serializers.CharField(source='caja.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Apertura
        fields = [
            'id', 'sede', 'sede_nombre', 'caja', 'caja_nombre',
            'usuario', 'usuario_nombre', 'monto_inicial', 'estado',
            'estado_display', 'fecha_apertura', 'fecha_cierre', 'observacion'
        ]
        read_only_fields = ['estado', 'fecha_apertura', 'fecha_cierre']


class AbrirCajaSerializer(serializers.Serializer):
    caja_id = serializers.IntegerField()
    monto_inicial = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = serializers.CharField(required=False, allow_blank=True)


class MovimientoCajaSerializer(serializers.ModelSerializer):
    tipo_movimiento_nombre = serializers.CharField(
        source='tipo_movimiento_caja.nombre', read_only=True
    )
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = MovimientoCaja
        fields = [
            'id', 'caja', 'apertura', 'usuario', 'usuario_nombre',
            'tipo_movimiento_caja', 'tipo_movimiento_nombre',
            'monto', 'tipo', 'tipo_display', 'concepto',
            'referencia_venta_id', 'fecha_movimiento'
        ]
        read_only_fields = ['fecha_movimiento']


class RegistrarMovimientoSerializer(serializers.Serializer):
    tipo_movimiento_caja_id = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    concepto = serializers.CharField(max_length=200)


class CierreDesgloseSerializer(serializers.ModelSerializer):
    metodo_pago_nombre = serializers.CharField(source='metodo_pago.nombre', read_only=True)

    class Meta:
        model = CierreDesglose
        fields = ['id', 'metodo_pago', 'metodo_pago_nombre', 'total']


class CierreCajaSerializer(serializers.ModelSerializer):
    usuario_cierre_nombre = serializers.CharField(
        source='usuario_cierre.nombre_usuario', read_only=True
    )
    desgloses = CierreDesgloseSerializer(many=True, read_only=True)

    class Meta:
        model = CierreCaja
        fields = [
            'id', 'apertura', 'usuario_cierre', 'usuario_cierre_nombre',
            'total_ventas', 'total_esperado', 'total_real', 'diferencia',
            'observacion', 'fecha_cierre', 'desgloses'
        ]
        read_only_fields = [
            'total_ventas', 'total_esperado', 'diferencia', 'fecha_cierre'
        ]


class CerrarCajaSerializer(serializers.Serializer):
    """Datos que el cajero ingresa al cerrar el turno."""
    total_real = serializers.DecimalField(max_digits=10, decimal_places=2)
    observacion = serializers.CharField(required=False, allow_blank=True)
    desgloses = CierreDesgloseSerializer(many=True, required=False)