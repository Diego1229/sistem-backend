from decimal import Decimal
from rest_framework import serializers
from .models import Proveedor, Compra, CompraDetalle, FacturaAbastecimiento, DevolucionCompra, DevolucionCompraDetalle


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = ['id', 'nombre', 'nit', 'telefono', 'email', 'direccion', 'ciudad', 'activo']

    def validate_nit(self, value):
        if not value:
            return value
        qs = Proveedor.objects.filter(nit=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Ya existe un proveedor con este NIT.')
        return value


class CompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = CompraDetalle
        fields = [
            'id', 'producto', 'producto_nombre',
            'cantidad', 'precio_unitario', 'subtotal', 'fecha_vencimiento'
        ]

    def validate(self, data):
        data['subtotal'] = data['cantidad'] * data['precio_unitario']
        return data


class CompraListSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero_compra', 'proveedor', 'proveedor_nombre',
            'sede', 'sede_nombre', 'usuario_nombre', 'estado',
            'estado_display', 'total', 'fecha_compra'
        ]


class CompraDetailSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    detalles = CompraDetalleSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero_compra', 'proveedor', 'proveedor_nombre',
            'sede', 'sede_nombre', 'usuario', 'usuario_nombre',
            'no_factura_proveedor', 'estado', 'estado_display',
            'total', 'observacion', 'fecha_compra', 'fecha_recepcion',
            'detalles'
        ]
        read_only_fields = ['numero_compra', 'total', 'fecha_compra', 'fecha_recepcion']


class CrearCompraSerializer(serializers.Serializer):
    """Serializer para crear una compra con sus detalles en una sola operación."""
    proveedor_id = serializers.IntegerField()
    sede_id = serializers.IntegerField()
    no_factura_proveedor = serializers.CharField(required=False, allow_blank=True)
    observacion = serializers.CharField(required=False, allow_blank=True)
    detalles = CompraDetalleSerializer(many=True)

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError('La compra debe tener al menos un producto.')
        return value


class RecibirCompraSerializer(serializers.Serializer):
    """Serializer para confirmar recepción de mercancía."""
    observacion = serializers.CharField(required=False, allow_blank=True)


class FacturaAbastecimientoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = FacturaAbastecimiento
        fields = [
            'id', 'compra', 'proveedor', 'proveedor_nombre',
            'sede', 'sede_nombre', 'numero_factura', 'subtotal',
            'total_iva', 'total', 'estado', 'fecha_emision'
        ]


class DevolucionCompraDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DevolucionCompraDetalle
        fields = ['id', 'compra_detalle', 'cantidad_devuelta']


class DevolucionCompraSerializer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    detalles = DevolucionCompraDetalleSerializer(many=True, read_only=True)

    class Meta:
        model = DevolucionCompra
        fields = [
            'id', 'compra', 'usuario', 'motivo', 'total_devuelto',
            'estado', 'estado_display', 'fecha_devolucion', 'detalles'
        ]
        read_only_fields = ['total_devuelto', 'estado', 'fecha_devolucion']


class DevolucionCompraDetalleInputSerializer(serializers.Serializer):
    """Línea de detalle recibida al crear una devolución a proveedor."""
    compra_detalle_id = serializers.IntegerField()
    cantidad_devuelta = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01')
    )


class CrearDevolucionCompraSerializer(serializers.Serializer):
    """Serializer para registrar una devolución a proveedor con sus líneas de detalle."""
    compra_id = serializers.IntegerField()
    motivo = serializers.CharField()
    detalles = DevolucionCompraDetalleInputSerializer(many=True)

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError('La devolución debe tener al menos un producto.')
        return value