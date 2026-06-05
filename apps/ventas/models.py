from django.db import models

# Create your models here.
from django.db import models
from apps.configuracion.models import Sede, Caja, MetodoPago
from apps.usuarios.models import Usuario
from apps.inventario.models import Producto
from apps.caja.models import Apertura


class Cliente(models.Model):
    """Cliente registrado. Opcional en la venta."""
    class TipoDocumento(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        NIT = 'NIT', 'NIT'
        CE = 'CE', 'Cédula de extranjería'
        PAS = 'PAS', 'Pasaporte'
        DE = 'DE', 'Documento extranjero'

    nombre = models.CharField(max_length=150)
    tipo_documento = models.CharField(
        max_length=3, choices=TipoDocumento.choices,
        null=True, blank=True
    )
    numero_documento = models.CharField(max_length=20, null=True, blank=True)
    razon_social = models.CharField(max_length=150, null=True, blank=True)
    email = models.EmailField(max_length=100, null=True, blank=True)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    notas = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cli_clientes'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    """Cabecera de una venta en el POS."""
    class Estado(models.TextChoices):
        COMPLETADA = 'completada', 'Completada'
        ANULADA = 'anulada', 'Anulada'
        DEVUELTA = 'devuelta', 'Devuelta'

    numero_venta = models.CharField(max_length=30, unique=True, null=True, blank=True)
    sede = models.ForeignKey(
        Sede, on_delete=models.PROTECT,
        db_column='sede_id', related_name='ventas'
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT,
        db_column='usuario_id', related_name='ventas'
    )
    apertura_caja = models.ForeignKey(
        Apertura, on_delete=models.PROTECT,
        db_column='apertura_caja_id', related_name='ventas'
    )
    caja = models.ForeignKey(
        Caja, on_delete=models.PROTECT,
        db_column='caja_id', related_name='ventas'
    )
    nombre_cliente = models.CharField(max_length=150, null=True, blank=True)
    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='cliente_id', related_name='ventas'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=10, choices=Estado.choices,
        default=Estado.COMPLETADA
    )
    observacion = models.TextField(null=True, blank=True)
    fecha_venta = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ven_ventas'
        managed = False
        ordering = ['-fecha_venta']

    def __str__(self):
        return f"{self.numero_venta} — ${self.total}"


class VentaDetalle(models.Model):
    """Línea de producto en una venta."""
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE,
        db_column='venta_id', related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT,
        db_column='producto_id', related_name='venta_detalles'
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'ven_venta_detalle'
        managed = False
        ordering = ['id']

    def __str__(self):
        return f"{self.producto.nombre} x{self.cantidad}"


class Pago(models.Model):
    """Pago asociado a una venta. Puede haber varios métodos."""
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE,
        db_column='venta_id', related_name='pagos'
    )
    metodo_pago = models.ForeignKey(
        MetodoPago, on_delete=models.PROTECT,
        db_column='metodo_pago_id', related_name='pagos'
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    referencia = models.CharField(max_length=100, null=True, blank=True)
    cambio = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_pago = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ven_pagos'
        managed = False
        ordering = ['id']

    def __str__(self):
        return f"{self.metodo_pago} — ${self.monto}"


class FacturaVenta(models.Model):
    """Factura DIAN de una venta."""
    class Estado(models.TextChoices):
        EMITIDA = 'emitida', 'Emitida'
        ANULADA = 'anulada', 'Anulada'

    venta = models.OneToOneField(
        Venta, on_delete=models.PROTECT,
        db_column='venta_id', related_name='factura'
    )
    sede = models.ForeignKey(
        Sede, on_delete=models.PROTECT,
        db_column='sede_id', related_name='facturas_venta'
    )
    numero_factura = models.CharField(max_length=50, unique=True)
    nombre_cliente = models.CharField(max_length=150, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=10, choices=Estado.choices,
        default=Estado.EMITIDA
    )
    cufe = models.CharField(max_length=200, null=True, blank=True)
    qr_code = models.TextField(null=True, blank=True)
    xml_dian = models.TextField(null=True, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ven_facturas'
        managed = False
        ordering = ['-fecha_emision']

    def __str__(self):
        return f"Factura {self.numero_factura}"


class DevolucionVenta(models.Model):
    """Devolución de una venta por parte del cliente."""
    class Estado(models.TextChoices):
        PENDIENTE = 'pendiente', 'Pendiente'
        APROBADA = 'aprobada', 'Aprobada'
        RECHAZADA = 'rechazada', 'Rechazada'

    venta = models.ForeignKey(
        Venta, on_delete=models.PROTECT,
        db_column='venta_id', related_name='devoluciones'
    )
    usuario = models.ForeignKey(
        Usuario, on_delete=models.PROTECT,
        db_column='usuario_id', related_name='devoluciones_venta'
    )
    motivo = models.TextField()
    total_devuelto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=10, choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    fecha_devolucion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ven_devoluciones'
        managed = False
        ordering = ['-fecha_devolucion']

    def __str__(self):
        return f"Devolución venta {self.venta.numero_venta}"


class DevolucionVentaDetalle(models.Model):
    """Detalle de productos devueltos."""
    devolucion = models.ForeignKey(
        DevolucionVenta, on_delete=models.CASCADE,
        db_column='devolucion_id', related_name='detalles'
    )
    venta_detalle = models.ForeignKey(
        VentaDetalle, on_delete=models.PROTECT,
        db_column='venta_detalle_id', related_name='devoluciones'
    )
    cantidad_devuelta = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'ven_devolucion_detalle'
        managed = False
        ordering = ['id']

    def __str__(self):
        return f"Detalle devolución #{self.devolucion_id}"