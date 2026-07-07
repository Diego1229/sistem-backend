from django.db import transaction
from django.utils import timezone
from .models import Compra, CompraDetalle, DevolucionCompra, DevolucionCompraDetalle
from apps.inventario.services import ajustar_stock
from apps.configuracion.models import TipoMovimientoInventario


def get_consecutivo(sede_id, modulo):
    """Llama al stored procedure para obtener el siguiente número."""
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.callproc('sp_siguiente_consecutivo', [sede_id, modulo, ''])
        cursor.execute('SELECT @_sp_siguiente_consecutivo_2')
        resultado = cursor.fetchone()[0]
    return resultado


def crear_compra(proveedor_id, sede_id, usuario, no_factura_proveedor='', observacion='', detalles=[]):
    """
    Crea una orden de compra en estado 'pendiente'.
    No mueve stock todavía — eso pasa al recibir.
    """
    with transaction.atomic():
        numero = get_consecutivo(sede_id, 'compras')

        compra = Compra.objects.create(
            numero_compra=numero,
            proveedor_id=proveedor_id,
            sede_id=sede_id,
            usuario=usuario,
            no_factura_proveedor=no_factura_proveedor,
            observacion=observacion,
            estado='pendiente',
            total=0
        )

        total = 0
        for item in detalles:
            subtotal = item['cantidad'] * item['precio_unitario']
            CompraDetalle.objects.create(
                compra=compra,
                producto_id=item['producto'].id,
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                subtotal=subtotal,
                fecha_vencimiento=item.get('fecha_vencimiento')
            )
            total += subtotal

        Compra.objects.filter(pk=compra.pk).update(total=total)
        compra.total = total
        return compra


def recibir_compra(compra_id, usuario, observacion=''):
    """
    Marca la compra como recibida y actualiza el stock de cada producto.
    Esta es la operación crítica — usa transaction.atomic().
    """
    with transaction.atomic():
        compra = Compra.objects.select_for_update().get(pk=compra_id)

        if compra.estado != 'pendiente':
            raise ValueError(f'Solo se pueden recibir compras en estado pendiente. Estado actual: {compra.estado}')

        tipo_entrada = TipoMovimientoInventario.objects.filter(
            nombre='Compra', tipo='entrada'
        ).first()

        if not tipo_entrada:
            raise ValueError('No existe el tipo de movimiento "Compra entrada" en la configuración.')

        detalles = CompraDetalle.objects.filter(compra=compra)

        for detalle in detalles:
            ajustar_stock(
                producto_id=detalle.producto_id,
                sede_id=compra.sede_id,
                cantidad=detalle.cantidad,
                tipo_movimiento_id=tipo_entrada.id,
                usuario=usuario,
                observacion=f'Recepción compra {compra.numero_compra}'
            )

        Compra.objects.filter(pk=compra.pk).update(
            estado='recibida',
            fecha_recepcion=timezone.now()
        )

        compra.refresh_from_db()
        return compra