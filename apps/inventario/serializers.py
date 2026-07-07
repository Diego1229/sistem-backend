from rest_framework import serializers
from .models import Categoria, Producto, ProductoCategoria, Inventario, Movimiento, Lote


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'imagen', 'activo']


class ProductoCategoriaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)

    class Meta:
        model = ProductoCategoria
        fields = ['id', 'categoria', 'categoria_nombre']


class ProductoListSerializer(serializers.ModelSerializer):
    """Vista resumida para listar productos."""
    impuesto_nombre = serializers.CharField(source='impuesto.nombre', read_only=True)
    categorias = ProductoCategoriaSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'codigo_barras', 'sku',
            'precio_venta', 'impuesto_nombre', 'imagen',
            'unidad_medida', 'controla_stock', 'activo',
            'categorias'
        ]


class ProductoDetailSerializer(serializers.ModelSerializer):
    """Vista completa para crear y editar productos."""
    impuesto_nombre = serializers.CharField(source='impuesto.nombre', read_only=True)
    categorias = ProductoCategoriaSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'nombre', 'descripcion', 'codigo_barras', 'sku',
            'precio_compra', 'precio_venta', 'impuesto', 'impuesto_nombre',
            'imagen', 'unidad_medida', 'controla_stock', 'permite_decimal',
            'activo', 'categorias', 'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']

    def validate_precio_venta(self, value):
        if value <= 0:
            raise serializers.ValidationError('El precio de venta debe ser mayor a cero.')
        return value


class InventarioSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    bajo_minimo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventario
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_sku',
            'sede', 'sede_nombre', 'cantidad', 'stock_minimo',
            'stock_maximo', 'bajo_minimo', 'ultima_actualizacion'
        ]
        read_only_fields = ['cantidad', 'ultima_actualizacion']


class MovimientoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)
    tipo_nombre = serializers.CharField(source='tipo_movimiento.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.nombre_usuario', read_only=True)

    class Meta:
        model = Movimiento
        fields = [
            'id', 'producto', 'producto_nombre', 'sede', 'sede_nombre',
            'tipo_movimiento', 'tipo_nombre', 'cantidad',
            'stock_antes', 'stock_despues', 'usuario', 'usuario_nombre',
            'observacion', 'fecha_movimiento'
        ]
        read_only_fields = ['stock_antes', 'stock_despues', 'fecha_movimiento']


class AjusteStockSerializer(serializers.Serializer):
    """Serializer para ajustes manuales de stock (solo admin)."""
    producto_id = serializers.IntegerField()
    sede_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2)
    tipo_movimiento_id = serializers.IntegerField()
    observacion = serializers.CharField(required=False, allow_blank=True)


class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = Lote
        fields = [
            'id', 'producto', 'producto_nombre', 'sede', 'sede_nombre',
            'numero_lote', 'fecha_vencimiento', 'cantidad', 'activo'
        ]