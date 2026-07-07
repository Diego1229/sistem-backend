from django.db import models
from apps.configuracion.models import Sede, Impuesto, TipoMovimientoInventario
from apps.usuarios.models import Usuario

class Categoria(models.Model):
    """Categorías de productos. Un producto puede tener varias."""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    imagen = models.CharField(max_length=300, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inv_categorias'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    """Catálogo maestro de productos."""
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True, null=True)
    codigo_barras = models.CharField(max_length=50, unique=True, blank=True, null=True)
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto = models.ForeignKey(
        Impuesto,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='impuesto_id',
        related_name='productos'
    )
    imagen = models.CharField(max_length=300, blank=True, null=True)
    unidad_medida = models.CharField(max_length=30, blank=True, null=True)
    controla_stock = models.BooleanField(default=True)
    permite_decimal = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'inv_productos'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class ProductoCategoria(models.Model):
    """Relación muchos a muchos entre productos y categorías."""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column='producto_id',
        related_name='categorias'
    )
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.CASCADE,
        db_column='categoria_id',
        related_name='productos'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inv_producto_categoria'
        managed = False
        unique_together = [['producto', 'categoria']]

    def __str__(self):
        return f"{self.producto} — {self.categoria}"


class Inventario(models.Model):
    """Stock actual de cada producto por sede."""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column='producto_id',
        related_name='stocks'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        db_column='sede_id',
        related_name='stocks'
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_maximo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inv_stock'
        managed = False
        unique_together = [['producto', 'sede']]
        ordering = ['producto__nombre']

    def __str__(self):
        return f"{self.producto.nombre} @ {self.sede.nombre}: {self.cantidad}"

    @property
    def bajo_minimo(self):
        return self.cantidad <= self.stock_minimo


class Movimiento(models.Model):
    """
    Historial completo de movimientos de inventario.
    Nunca se borra — es la bitácora del stock.
    """
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column='producto_id',
        related_name='movimientos'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='movimientos'
    )
    tipo_movimiento = models.ForeignKey(
        TipoMovimientoInventario,
        on_delete=models.PROTECT,
        db_column='tipo_movimiento_id',
        related_name='movimientos'
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    stock_antes = models.DecimalField(max_digits=10, decimal_places=2)
    stock_despues = models.DecimalField(max_digits=10, decimal_places=2)
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_id',
        related_name='movimientos_inventario'
    )
    venta_detalle_id = models.IntegerField(null=True, blank=True)
    compra_detalle_id = models.IntegerField(null=True, blank=True)
    venta_devolucion_id = models.IntegerField(null=True, blank=True)
    compra_devolucion_id = models.IntegerField(null=True, blank=True)
    observacion = models.TextField(blank=True, null=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inv_movimientos'
        managed = False
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.tipo_movimiento} — {self.producto} ({self.cantidad})"


class Lote(models.Model):
    """Lotes de productos con fecha de vencimiento."""
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column='producto_id',
        related_name='lotes'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='lotes'
    )
    compra_detalle_id = models.IntegerField(null=True, blank=True)
    numero_lote = models.CharField(max_length=50)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'inv_lotes'
        managed = False
        ordering = ['fecha_vencimiento']

    def __str__(self):
        return f"Lote {self.numero_lote} — {self.producto.nombre}"
