from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import Venta, VentaDetalle, Pago, DevolucionVenta, DevolucionVentaDetalle
from apps.inventario.models import Producto
from apps.inventario.services import ajustar_stock
from apps.configuracion.models import TipoMovimientoInventario, MetodoPago
from apps.caja.models import MovimientoCaja, Apertura
from apps.caja.services import get_apertura_activa
from apps.usuarios.permissions import es_admin

DESCUENTO_MAXIMO_VENDEDOR_PCT = Decimal('10')


def get_consecutivo(sede_id, modulo):
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.callproc('sp_siguiente_consecutivo', [sede_id, modulo, ''])
        cursor.execute('SELECT @_sp_siguiente_consecutivo_2')
        resultado = cursor.fetchone()[0]
    return resultado


def crear_venta(usuario, sede_id, items, pagos, descuento=0,
                nombre_cliente='', cliente_id=None, observacion=''):
    """
    Crea una venta completa:
    1. Valida caja abierta
    2. Valida stock de cada producto
    3. Crea venta, detalles y pagos
    4. Descuenta stock
    5. Registra movimiento en caja
    """
    with transaction.atomic():

        # 1 — Verificar caja abierta
        apertura = get_apertura_activa(sede_id=sede_id, usuario=usuario)
        if not apertura and es_admin(usuario, sede_id):
            # Solo el admin puede vender usando cualquier apertura activa de la sede.
            # Un vendedor SIEMPRE debe usar su propio turno abierto.
            apertura = get_apertura_activa(sede_id=sede_id)
        if not apertura:
            raise ValueError('No hay caja abierta en esta sede. Abra un turno antes de vender.')

        # 2 — Obtener tipos de movimiento
        tipo_venta = TipoMovimientoInventario.objects.filter(
            nombre='Venta', tipo='salida'
        ).first()
        if not tipo_venta:
            raise ValueError('No existe el tipo de movimiento "Venta salida". Verifique la configuración.')

        # 3 — Validar stock y calcular total
        total = Decimal('0.00')
        detalles_preparados = []

        for item in items:
            producto = Producto.objects.select_for_update().get(pk=item['producto_id'])

            if producto.controla_stock:
                from apps.inventario.models import Inventario
                try:
                    inv = Inventario.objects.get(
                        producto=producto, sede_id=sede_id
                    )
                    if inv.cantidad < item['cantidad']:
                        raise ValueError(
                            f'Stock insuficiente para "{producto.nombre}". '
                            f'Disponible: {inv.cantidad}, solicitado: {item["cantidad"]}'
                        )
                except Inventario.DoesNotExist:
                    raise ValueError(
                        f'El producto "{producto.nombre}" no tiene stock registrado en esta sede.'
                    )

            subtotal = (item['cantidad'] * item['precio_unitario']) - item.get('descuento', 0)
            total += subtotal
            detalles_preparados.append({
                'producto': producto,
                'cantidad': item['cantidad'],
                'precio_unitario': item['precio_unitario'],
                'descuento': item.get('descuento', Decimal('0.00')),
                'subtotal': subtotal
            })

        # 3.5 — Validar límite de descuento (10% sin aprobación, más solo admin)
        descuento_dec = Decimal(str(descuento))
        if descuento_dec > 0 and total > 0:
            porcentaje_descuento = (descuento_dec / total) * 100
            if porcentaje_descuento > DESCUENTO_MAXIMO_VENDEDOR_PCT and not es_admin(usuario, sede_id):
                raise ValueError(
                    f'El descuento (${descuento_dec}, {porcentaje_descuento:.1f}%) supera el '
                    f'{DESCUENTO_MAXIMO_VENDEDOR_PCT}% permitido para vendedores. '
                    f'Se requiere aprobación de un administrador.'
                )

        total_con_descuento = total - descuento_dec

        # 4 — Validar que el pago cubra el total
        total_pagado = sum(Decimal(str(p['monto'])) for p in pagos)
        if total_pagado < total_con_descuento:
            raise ValueError(
                f'El monto pagado (${total_pagado}) no cubre el total '
                f'de la venta (${total_con_descuento}).'
            )

        # 5 — Crear la venta
        numero = get_consecutivo(sede_id, 'ventas')
        venta = Venta.objects.create(
            numero_venta=numero,
            sede_id=sede_id,
            usuario=usuario,
            apertura_caja=apertura,
            caja=apertura.caja,
            nombre_cliente=nombre_cliente or None,
            cliente_id=cliente_id,
            total=total_con_descuento,
            descuento=descuento,
            observacion=observacion,
            estado='completada'
        )

        # 6 — Crear detalles y descontar stock
        for detalle in detalles_preparados:
            vd = VentaDetalle.objects.create(
                venta=venta,
                producto=detalle['producto'],
                cantidad=detalle['cantidad'],
                precio_unitario=detalle['precio_unitario'],
                descuento=detalle['descuento'],
                subtotal=detalle['subtotal']
            )
            if detalle['producto'].controla_stock:
                ajustar_stock(
                    producto_id=detalle['producto'].id,
                    sede_id=sede_id,
                    cantidad=detalle['cantidad'],
                    tipo_movimiento_id=tipo_venta.id,
                    usuario=usuario,
                    observacion=f'Venta {numero}'
                )

        # 7 — Registrar pagos
        cambio_total = total_pagado - total_con_descuento
        for i, pago_data in enumerate(pagos):
            cambio = cambio_total if i == len(pagos) - 1 else Decimal('0.00')
            Pago.objects.create(
                venta=venta,
                metodo_pago_id=pago_data['metodo_pago_id'],
                monto=pago_data['monto'],
                referencia=pago_data.get('referencia', ''),
                cambio=cambio
            )

        # 8 — Registrar ingreso en caja
        from apps.configuracion.models import TipoMovimientoCaja
        tipo_mov_caja = TipoMovimientoCaja.objects.filter(nombre='Venta').first()
        MovimientoCaja.objects.create(
            caja=apertura.caja,
            apertura=apertura,
            usuario=usuario,
            tipo_movimiento_caja=tipo_mov_caja,
            monto=total_con_descuento,
            tipo='entrada',
            concepto=f'Venta {numero}',
            referencia_venta_id=venta.id
        )

        return venta


def anular_venta(venta_id, usuario, motivo=''):
    """
    Anula una venta y devuelve el stock.
    Solo admin puede anular.
    """
    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(pk=venta_id)

        if venta.estado == 'anulada':
            raise ValueError('Esta venta ya está anulada.')

        tipo_devolucion = TipoMovimientoInventario.objects.filter(
            nombre='Devolución cliente', tipo='entrada'
        ).first()

        # Devolver stock de cada producto
        for detalle in venta.detalles.select_related('producto'):
            if detalle.producto.controla_stock and tipo_devolucion:
                ajustar_stock(
                    producto_id=detalle.producto_id,
                    sede_id=venta.sede_id,
                    cantidad=detalle.cantidad,
                    tipo_movimiento_id=tipo_devolucion.id,
                    usuario=usuario,
                    observacion=f'Anulación venta {venta.numero_venta}'
                )

        Venta.objects.filter(pk=venta.pk).update(estado='anulada')
        venta.refresh_from_db()
        return venta


def crear_devolucion_venta(venta_id, usuario, motivo, detalles):
    """
    Crea una devolución parcial de cliente en estado 'pendiente' con sus
    líneas de detalle. No mueve stock todavía — eso ocurre al aprobar
    (ver aprobar_devolucion_venta), igual que en anular_venta().
    """
    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(pk=venta_id)

        if venta.estado == 'anulada':
            raise ValueError('No se puede registrar una devolución sobre una venta anulada.')

        devolucion = DevolucionVenta.objects.create(
            venta=venta,
            usuario=usuario,
            motivo=motivo,
            estado='pendiente',
            total_devuelto=0
        )

        total = Decimal('0.00')
        for item in detalles:
            try:
                venta_detalle = VentaDetalle.objects.get(
                    pk=item['venta_detalle_id'], venta=venta
                )
            except VentaDetalle.DoesNotExist:
                raise ValueError('Uno de los productos no pertenece a esta venta.')

            cantidad_devuelta = item['cantidad_devuelta']
            if cantidad_devuelta > venta_detalle.cantidad:
                raise ValueError(
                    f'No se puede devolver más de lo vendido para '
                    f'"{venta_detalle.producto.nombre}" (vendido: {venta_detalle.cantidad}).'
                )

            DevolucionVentaDetalle.objects.create(
                devolucion=devolucion,
                venta_detalle=venta_detalle,
                cantidad_devuelta=cantidad_devuelta
            )
            total += cantidad_devuelta * venta_detalle.precio_unitario

        DevolucionVenta.objects.filter(pk=devolucion.pk).update(total_devuelto=total)
        devolucion.refresh_from_db()
        return devolucion


def aprobar_devolucion_venta(devolucion_id, usuario):
    """
    Aprueba una devolución de cliente: devuelve el stock de cada producto
    devuelto usando ajustar_stock(), igual que hace anular_venta().
    """
    with transaction.atomic():
        devolucion = DevolucionVenta.objects.select_for_update().get(pk=devolucion_id)

        if devolucion.estado != 'pendiente':
            raise ValueError('Solo se pueden aprobar devoluciones pendientes.')

        tipo_entrada = TipoMovimientoInventario.objects.filter(
            nombre='Devolución cliente', tipo='entrada'
        ).first()
        if not tipo_entrada:
            raise ValueError(
                'No existe el tipo de movimiento "Devolución cliente" en la configuración.'
            )

        detalles = devolucion.detalles.select_related('venta_detalle__producto')
        if not detalles.exists():
            raise ValueError('Esta devolución no tiene productos registrados.')

        for detalle in detalles:
            producto = detalle.venta_detalle.producto
            if producto.controla_stock:
                ajustar_stock(
                    producto_id=producto.id,
                    sede_id=devolucion.venta.sede_id,
                    cantidad=detalle.cantidad_devuelta,
                    tipo_movimiento_id=tipo_entrada.id,
                    usuario=usuario,
                    observacion=(
                        f'Devolución de cliente #{devolucion.id} — '
                        f'Venta {devolucion.venta.numero_venta}'
                    )
                )

        DevolucionVenta.objects.filter(pk=devolucion.pk).update(estado='aprobada')
        devolucion.refresh_from_db()
        return devolucion