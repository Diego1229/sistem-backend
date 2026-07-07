from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone
from .models import Apertura, MovimientoCaja, CierreCaja, CierreDesglose
from apps.configuracion.models import Caja, TipoMovimientoCaja


def abrir_caja(caja_id, sede_id, usuario, monto_inicial=0, observacion=''):
    """
    Abre un turno de caja.
    Valida que no haya una apertura activa en esa caja.
    """
    with transaction.atomic():
        caja = Caja.objects.get(pk=caja_id)

        # Verificar que no haya turno activo en esta caja
        apertura_activa = Apertura.objects.filter(
            caja=caja,
            estado='abierta'
        ).first()

        if apertura_activa:
            raise ValueError(
                f'La caja "{caja.nombre}" ya tiene un turno abierto '
                f'por el usuario {apertura_activa.usuario.nombre_usuario}.'
            )

        apertura = Apertura.objects.create(
            sede_id=sede_id,
            caja=caja,
            usuario=usuario,
            monto_inicial=monto_inicial,
            estado='abierta',
            observacion=observacion
        )

        # Registrar movimiento de apertura
        tipo_apertura = TipoMovimientoCaja.objects.filter(nombre='Apertura caja').first()
        if monto_inicial > 0 and tipo_apertura:
            MovimientoCaja.objects.create(
                caja=caja,
                apertura=apertura,
                usuario=usuario,
                tipo_movimiento_caja=tipo_apertura,
                monto=monto_inicial,
                tipo='entrada',
                concepto=f'Monto inicial apertura #{apertura.id}'
            )

        return apertura


def cerrar_caja(apertura_id, usuario, total_real, observacion='', desgloses=[]):
    """
    Cierra un turno de caja.
    Calcula total esperado, diferencia y registra el cierre.
    """
    with transaction.atomic():
        apertura = Apertura.objects.select_for_update().get(pk=apertura_id)

        if apertura.estado != 'abierta':
            raise ValueError('Este turno de caja ya está cerrado.')

        # Calcular total esperado sumando todos los movimientos
        totales = MovimientoCaja.objects.filter(apertura=apertura).aggregate(
            entradas=Sum('monto', filter=Q(tipo='entrada')),
            salidas=Sum('monto', filter=Q(tipo='salida'))
        )
        entradas = totales['entradas'] or 0
        salidas = totales['salidas'] or 0
        total_esperado = entradas - salidas

        # Calcular total ventas
        total_ventas = MovimientoCaja.objects.filter(
            apertura=apertura,
            tipo='entrada',
            referencia_venta_id__isnull=False
        ).aggregate(total=Sum('monto'))['total'] or 0

        diferencia = total_real - total_esperado

        # Crear cierre
        cierre = CierreCaja.objects.create(
            apertura=apertura,
            usuario_cierre=usuario,
            total_ventas=total_ventas,
            total_esperado=total_esperado,
            total_real=total_real,
            diferencia=diferencia,
            observacion=observacion
        )

        # Guardar desgloses por método de pago
        for desglose in desgloses:
            CierreDesglose.objects.create(
                cierre_caja=cierre,
                metodo_pago_id=desglose['metodo_pago'].id,
                total=desglose['total']
            )

        # Cerrar apertura
        Apertura.objects.filter(pk=apertura.pk).update(
            estado='cerrada',
            fecha_cierre=timezone.now()
        )

        return cierre


def get_apertura_activa(caja_id=None, sede_id=None, usuario=None):
    """
    Busca la apertura activa. Puede filtrar por caja, sede o usuario.
    Retorna None si no hay ninguna activa.
    """
    qs = Apertura.objects.filter(estado='abierta')
    if caja_id:
        qs = qs.filter(caja_id=caja_id)
    if sede_id:
        qs = qs.filter(sede_id=sede_id)
    if usuario:
        qs = qs.filter(usuario=usuario)
    return qs.first()