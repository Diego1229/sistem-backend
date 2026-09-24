from django.db import transaction
from django.utils import timezone
from .models import Compra, CompraDetalle, DevolucionCompra, DevolucionCompraDetalle
from apps.inventario.services import ajustar_stock
from apps.configuracion.models import TipoMovimientoInventario


def crear_devolucion_compra(compra_id, usuario, motivo, detalles):
    """
    Crea una devolución a proveedor en estado 'pendiente' con sus líneas de detalle.
    No mueve stock todavía — eso ocurre al aprobar (ver aprobar_devolucion_compra).
    """
    with transaction.atomic():
        compra = Compra.objects.select_for_update().get(pk=compra_id)

        if compra.estado != 'recibida':
            raise ValueError('Solo se pueden devolver productos de compras ya recibidas.')

        devolucion = DevolucionCompra.objects.create(
            compra=compra,
            usuario=usuario,
            motivo=motivo,
            estado='pendiente',
            total_devuelto=0
        )

        total = 0
        for item in detalles:
            try:
                compra_detalle = CompraDetalle.objects.get(
                    pk=item['compra_detalle_id'], compra=compra
                )
            except CompraDetalle.DoesNotExist:
                raise ValueError('Uno de los productos no pertenece a esta compra.')

            cantidad_devuelta = item['cantidad_devuelta']
            if cantidad_devuelta > compra_detalle.cantidad:
                raise ValueError(
                    f'No se puede devolver más de lo comprado para '
                    f'"{compra_detalle.producto.nombre}" (comprado: {compra_detalle.cantidad}).'
                )

            DevolucionCompraDetalle.objects.create(
                devolucion=devolucion,
                compra_detalle=compra_detalle,
                cantidad_devuelta=cantidad_devuelta
            )
            total += cantidad_devuelta * compra_detalle.precio_unitario

        DevolucionCompra.objects.filter(pk=devolucion.pk).update(total_devuelto=total)
        devolucion.refresh_from_db()
        return devolucion


def aprobar_devolucion_compra(devolucion_id, usuario):
    """
    Aprueba una devolución a proveedor: descuenta el stock de cada producto
    devuelto usando ajustar_stock(), igual que hace recibir_compra() al entrar.
    """
    with transaction.atomic():
        devolucion = DevolucionCompra.objects.select_for_update().get(pk=devolucion_id)

        if devolucion.estado != 'pendiente':
            raise ValueError('Solo se pueden aprobar devoluciones pendientes.')

        tipo_salida = TipoMovimientoInventario.objects.filter(
            nombre='Devolución proveedor', tipo='salida'
        ).first()
        if not tipo_salida:
            raise ValueError(
                'No existe el tipo de movimiento "Devolución proveedor" en la configuración.'
            )

        detalles = devolucion.detalles.select_related('compra_detalle__producto')
        if not detalles.exists():
            raise ValueError('Esta devolución no tiene productos registrados.')

        for detalle in detalles:
            producto = detalle.compra_detalle.producto
            ajustar_stock(
                producto_id=producto.id,
                sede_id=devolucion.compra.sede_id,
                cantidad=detalle.cantidad_devuelta,
                tipo_movimiento_id=tipo_salida.id,
                usuario=usuario,
                observacion=(
                    f'Devolución a proveedor #{devolucion.id} — '
                    f'Compra {devolucion.compra.numero_compra}'
                )
            )

        DevolucionCompra.objects.filter(pk=devolucion.pk).update(estado='aprobada')
        devolucion.refresh_from_db()
        return devolucion


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