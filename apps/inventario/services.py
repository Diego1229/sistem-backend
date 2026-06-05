from django.db import transaction
from .models import Inventario, Movimiento, Producto
from apps.configuracion.models import TipoMovimientoInventario


def ajustar_stock(producto_id, sede_id, cantidad, tipo_movimiento_id, usuario, observacion=''):
    """
    Ajusta el stock de un producto en una sede.
    Crea el registro en inv_movimientos y actualiza inv_stock.
    Usa select_for_update para evitar condiciones de carrera.
    """
    with transaction.atomic():
        tipo = TipoMovimientoInventario.objects.get(pk=tipo_movimiento_id)
        producto = Producto.objects.get(pk=producto_id)

        # Obtener o crear el registro de inventario
        registro, creado = Inventario.objects.select_for_update().get_or_create(
            producto_id=producto_id,
            sede_id=sede_id,
            defaults={'cantidad': 0, 'stock_minimo': 0}
        )

        stock_antes = registro.cantidad

        if tipo.tipo == 'entrada':
            stock_despues = stock_antes + cantidad
        elif tipo.tipo == 'salida':
            if stock_antes < cantidad and producto.controla_stock:
                raise ValueError(
                    f'Stock insuficiente. Disponible: {stock_antes}, solicitado: {cantidad}'
                )
            stock_despues = stock_antes - cantidad
        else:
            # ajuste — cantidad puede ser positiva o negativa
            stock_despues = stock_antes + cantidad

        if stock_despues < 0 and producto.controla_stock:
            raise ValueError('El stock no puede quedar negativo.')

        # Actualizar inventario
        Inventario.objects.filter(pk=registro.pk).update(
            cantidad=stock_despues
        )

        # Registrar movimiento
        movimiento = Movimiento.objects.create(
            producto_id=producto_id,
            sede_id=sede_id,
            tipo_movimiento_id=tipo_movimiento_id,
            cantidad=cantidad,
            stock_antes=stock_antes,
            stock_despues=stock_despues,
            usuario=usuario,
            observacion=observacion
        )

        return movimiento, stock_despues