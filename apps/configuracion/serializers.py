from rest_framework import serializers
from .models import (
    Sede, MetodoPago, TipoMovimientoInventario,
    TipoMovimientoCaja, Impuesto, Caja, Consecutivo
)


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = [
            'id', 'nombre', 'telefono', 'whatsapp',
            'whatsapp_mensaje_plantilla', 'direccion',
            'ciudad', 'pais', 'activo'
        ]


class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = ['id', 'nombre', 'requiere_referencia', 'activo']


class TipoMovimientoInvSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = TipoMovimientoInventario
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'descripcion', 'activo']


class TipoMovimientoCajaSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = TipoMovimientoCaja
        fields = ['id', 'nombre', 'tipo', 'tipo_display', 'activo']


class ImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuesto
        fields = ['id', 'nombre', 'porcentaje', 'activo']


class CajaSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = Caja
        fields = ['id', 'sede', 'sede_nombre', 'nombre', 'codigo', 'activo']


class ConsecutivoSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = Consecutivo
        fields = [
            'id', 'sede', 'sede_nombre', 'modulo',
            'prefijo', 'numero_actual', 'longitud', 'activo'
        ]
        read_only_fields = ['numero_actual']  # solo se modifica via stored procedure