from django.db import models
from apps.configuracion.models import Sede, Caja, MetodoPago, TipoMovimientoCaja
from apps.usuarios.models import Usuario


class Apertura(models.Model):
    """
    Turno de caja. Sin apertura activa no se puede vender.
    Una caja solo puede tener una apertura activa a la vez.
    """
    class Estado(models.TextChoices):
        ABIERTA = 'abierta', 'Abierta'
        CERRADA = 'cerrada', 'Cerrada'

    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='aperturas'
    )
    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        db_column='caja_id',
        related_name='aperturas'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_id',
        related_name='aperturas'
    )
    monto_inicial = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.ABIERTA)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    observacion = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'caj_aperturas'
        managed = False
        ordering = ['-fecha_apertura']

    def __str__(self):
        return f"Apertura {self.id} — {self.caja} ({self.estado})"


class MovimientoCaja(models.Model):
    """
    Cada entrada o salida de dinero en la caja durante un turno.
    Las ventas generan movimientos automáticamente.
    """
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'

    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        db_column='caja_id',
        related_name='movimientos'
    )
    apertura = models.ForeignKey(
        Apertura,
        on_delete=models.PROTECT,
        db_column='apertura_caja_id',
        related_name='movimientos'
    )
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_id',
        related_name='movimientos_caja'
    )
    tipo_movimiento_caja = models.ForeignKey(
        TipoMovimientoCaja,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='tipo_movimiento_caja_id',
        related_name='movimientos'
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    concepto = models.CharField(max_length=200)
    referencia_venta_id = models.IntegerField(null=True, blank=True)
    compra_id = models.IntegerField(null=True, blank=True)
    fecha_movimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'caj_movimientos'
        managed = False
        ordering = ['-fecha_movimiento']

    def __str__(self):
        return f"{self.tipo} ${self.monto} — {self.concepto}"


class CierreCaja(models.Model):
    """Arqueo y cierre de un turno de caja."""
    apertura = models.OneToOneField(
        Apertura,
        on_delete=models.PROTECT,
        db_column='apertura_caja_id',
        related_name='cierre'
    )
    usuario_cierre = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        db_column='usuario_cierre_id',
        related_name='cierres_caja'
    )
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_esperado = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_real = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observacion = models.TextField(blank=True, null=True)
    fecha_cierre = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'caj_cierres'
        managed = False
        ordering = ['-fecha_cierre']

    def __str__(self):
        return f"Cierre apertura #{self.apertura_id} — diferencia: {self.diferencia}"


class CierreDesglose(models.Model):
    """Desglose del cierre por método de pago."""
    cierre_caja = models.ForeignKey(
        CierreCaja,
        on_delete=models.CASCADE,
        db_column='cierre_caja_id',
        related_name='desgloses'
    )
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        db_column='metodo_pago_id',
        related_name='desgloses_cierre'
    )
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'caj_cierre_desglose'
        managed = False
        unique_together = [['cierre_caja', 'metodo_pago']]

    def __str__(self):
        return f"{self.metodo_pago} — ${self.total}"