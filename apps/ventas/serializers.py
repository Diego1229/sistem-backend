from rest_framework import serializers
from .models import Cliente, Venta, VentaDetalle, Pago, FacturaVenta, DevolucionVenta, DevolucionVentaDetalle


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'tipo_documento', 'numero_documento',
            'razon_social', 'email', 'telefono', 'notas', 'activo'
        ]


class PagoSerializer(serializers.ModelSerializer):
    metodo_pago_nombre = serializers.CharField(source='metodo_pago.nombre', read_only=True)

    class Meta:
        model = Pago
        fields = ['id', 'metodo_pago', 'metodo_pago_nombre', 'monto', 'referencia', 'cambio']


class VentaDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = VentaDetalle
        fields = [
            'id', 'producto', 'producto_nombre',
            'cantidad', 'precio_unitario', 'descuento', 'subtotal'
        ]


class VentaListSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'numero_venta', 'sede_nombre', 'usuario_nombre',
            'nombre_cliente', 'total', 'descuento', 'estado',
            'estado_display', 'fecha_venta'
        ]


class VentaDetailSerializer(serializers.ModelSerializer):
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    detalles = VentaDetalleSerializer(many=True, read_only=True)
    pagos = PagoSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'numero_venta', 'sede', 'sede_nombre',
            'usuario', 'usuario_nombre', 'apertura_caja', 'caja',
            'nombre_cliente', 'cliente', 'total', 'descuento',
            'estado', 'estado_display', 'observacion',
            'fecha_venta', 'detalles', 'pagos'
        ]


class ItemVentaSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = serializers.DecimalField(max_digits=10, decimal_places=2)
    descuento = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)


class ItemPagoSerializer(serializers.Serializer):
    metodo_pago_id = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=10, decimal_places=2)
    referencia = serializers.CharField(required=False, allow_blank=True)


class CrearVentaSerializer(serializers.Serializer):
    """Serializer principal para crear una venta completa."""
    nombre_cliente = serializers.CharField(required=False, allow_blank=True)
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    descuento = serializers.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = serializers.CharField(required=False, allow_blank=True)
    items = ItemVentaSerializer(many=True)
    pagos = ItemPagoSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('La venta debe tener al menos un producto.')
        return value

    def validate_pagos(self, value):
        if not value:
            raise serializers.ValidationError('La venta debe tener al menos un método de pago.')
        return value

    def validate_descuento(self, value):
        if value < 0:
            raise serializers.ValidationError('El descuento no puede ser negativo.')
        return value


class FacturaVentaSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacturaVenta
        fields = [
            'id', 'venta', 'sede', 'numero_factura', 'nombre_cliente',
            'subtotal', 'total_iva', 'total', 'estado', 'fecha_emision'
        ]


class DevolucionVentaDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevolucionVentaDetalle
        fields = ['id', 'venta_detalle', 'cantidad_devuelta']


class DevolucionVentaSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    detalles = DevolucionVentaDetalleSerializer(many=True, read_only=True)

    class Meta:
        model = DevolucionVenta
        fields = [
            'id', 'venta', 'usuario', 'motivo', 'total_devuelto',
            'estado', 'estado_display', 'fecha_devolucion', 'detalles'
        ]
        read_only_fields = ['total_devuelto', 'estado', 'fecha_devolucion']


class AnularVentaSerializer(serializers.Serializer):
    motivo = serializers.CharField()