from django.db import models


class Sede(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    whatsapp = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_mensaje_plantilla = models.TextField(blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    ciudad = models.CharField(max_length=80, blank=True, null=True)
    pais = models.CharField(max_length=80, default='Colombia')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cfg_sedes'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MetodoPago(models.Model):
    nombre = models.CharField(max_length=80, unique=True)
    requiere_referencia = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cfg_metodos_pago'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class TipoMovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'
        AJUSTE = 'ajuste', 'Ajuste'

    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cfg_tipo_movimiento_inv'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class TipoMovimientoCaja(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'

    nombre = models.CharField(max_length=80, unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cfg_tipo_movimiento_caja'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


class Impuesto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cfg_impuestos'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}%)"


class Caja(models.Model):
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='cajas'
    )
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=30, unique=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cfg_cajas'
        managed = True
        ordering = ['sede', 'nombre']

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class Consecutivo(models.Model):
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='consecutivos'
    )
    modulo = models.CharField(max_length=50)
    prefijo = models.CharField(max_length=10)
    numero_actual = models.IntegerField(default=0)
    longitud = models.IntegerField(default=6)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'cfg_consecutivos'
        managed = True
        ordering = ['sede', 'modulo']
        unique_together = [['sede', 'modulo']]

    def __str__(self):
        return f"{self.sede.nombre} — {self.modulo} ({self.prefijo})"