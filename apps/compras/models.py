from django.db import models
from apps.configuracion.models import Sede
from apps.usuarios.models import Usuario
from apps.inventario.models import Producto


class Proveedor(models.Model):
    """Proveedores de mercancía."""
    nombre = models.CharField(max_length=150)
    nit = models.CharField(max_length=20, unique=True, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    ciudad = models.CharField(max_length=80, blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'com_proveedores'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    """Orden de compra a proveedor."""
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        RECIBIDA = 'recibida', 'Recibida'
        ANULADA = 'anulada', 'Anulada'

    numero_compra = models.CharField(max_length=30, unique=True, blank=True, null=True)
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        db_column='proveedor_id',
        related_name='compras'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='compras'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_id',
        related_name='compras'
    )
    no_factura_proveedor = models.CharField(max_length=80, blank=True, null=True)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = models.TextField(blank=True, null=True)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'com_compras'
        managed = False
        ordering = ['-fecha_compra']

    def __str__(self):
        return f"{self.numero_compra} — {self.proveedor.nombre}"


class CompraDetalle(models.Model):
    """Líneas de productos de una compra."""
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        db_column='compra_id',
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column='producto_id',
        related_name='compra_detalles'
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'com_compra_detalle'
        managed = False
        ordering = ['id']

    def __str__(self):
        return f"{self.compra} — {self.producto.nombre} x{self.cantidad}"


class FacturaAbastecimiento(models.Model):
    """Factura DIAN asociada a una compra."""
    class Estado(models.TextChoices):
        EMITIDA = 'emitida', 'Emitida'
        ANULADA = 'anulada', 'Anulada'

    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        db_column='proveedor_id',
        related_name='facturas'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='facturas_abastecimiento'
    )
    compra = models.ForeignKey(
        Compra,
        on_delete=models.PROTECT,
        db_column='compra_id',
        related_name='facturas'
    )
    numero_factura = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.EMITIDA)
    cufe = models.CharField(max_length=200, blank=True, null=True)
    qr_code = models.TextField(blank=True, null=True)
    xml_dian = models.TextField(blank=True, null=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'com_facturas_abastecimiento'
        managed = False
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Factura {self.numero_factura} — {self.proveedor.nombre}"


class DevolucionCompra(models.Model):
    """Devolución de mercancía a proveedor."""
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        APROBADA = 'aprobada', 'Aprobada'
        RECHAZADA = 'rechazada', 'Rechazada'

    compra = models.ForeignKey(
        Compra,
        on_delete=models.PROTECT,
        db_column='compra_id',
        related_name='devoluciones'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_id',
        related_name='devoluciones_compra'
    )
    motivo = models.TextField()
    total_devuelto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    fecha_devolucion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'com_devoluciones'
        managed = False
        ordering = ['-fecha_devolucion']

    def __str__(self):
        return f"Devolución #{self.id} — Compra {self.compra.numero_compra}"


class DevolucionCompraDetalle(models.Model):
    """Detalle de productos devueltos al proveedor."""
    devolucion = models.ForeignKey(
        DevolucionCompra,
        on_delete=models.CASCADE,
        db_column='devolucion_id',
        related_name='detalles'
    )
    compra_detalle = models.ForeignKey(
        CompraDetalle,
        on_delete=models.PROTECT,
        db_column='compra_detalle_id',
        related_name='devoluciones'
    )
    cantidad_devuelta = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'com_devolucion_detalle'
        managed = False
        ordering = ['id']

    def __str__(self):
        return f"Detalle devolución #{self.devolucion_id}"
