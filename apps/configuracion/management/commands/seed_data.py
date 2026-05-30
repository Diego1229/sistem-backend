from django.core.management.base import BaseCommand

from apps.configuracion.models import (
Sede,
Consecutivo,
MetodoPago,
Impuesto,
TipoMovimientoInventario,
TipoMovimientoCaja,
)

from apps.usuarios.models import (
Usuario,
Rol,
UsuarioRol,
)

class Command(BaseCommand):
    help = "Carga datos iniciales del sistema"

    def handle(self, *args, **kwargs):

        self.stdout.write("Creando datos iniciales...")

        # ==========================
        # ROLES
        # ==========================

        admin_rol, _ = Rol.objects.get_or_create(
            nombre="admin",
            defaults={
                "descripcion": "Acceso total al sistema"
            }
        )

        vendedor_rol, _ = Rol.objects.get_or_create(
            nombre="vendedor",
            defaults={
                "descripcion": "Acceso limitado a operaciones de venta"
            }
        )

        # ==========================
        # SEDE PRINCIPAL
        # ==========================

        sede, _ = Sede.objects.get_or_create(
            nombre="Sede Principal",
            defaults={
                "ciudad": "Medellín",
                "pais": "Colombia"
            }
        )

        # ==========================
        # USUARIO ADMIN
        # ==========================

        usuario, creado = Usuario.objects.get_or_create(
            nombre_usuario="admin",
            defaults={
                "documento": "000000000",
                "email": "admin@sistem.co",
                "activo": True,
            }
        )

        if creado:
            usuario.set_password("admin123")
            usuario.save()

        # ==========================
        # ROL ADMIN EN LA SEDE
        # ==========================

        UsuarioRol.objects.get_or_create(
            usuario=usuario,
            rol=admin_rol,
            sede=sede,
            defaults={
                "activo": True
            }
        )

        # ==========================
        # CONSECUTIVOS
        # ==========================

        consecutivos = [
            ("ventas", "VTA"),
            ("compras", "COM"),
            ("pedidos", "PED"),
            ("facturas", "FAC"),
        ]

        for modulo, prefijo in consecutivos:
            Consecutivo.objects.get_or_create(
                sede=sede,
                modulo=modulo,
                defaults={
                    "prefijo": prefijo,
                    "numero_actual": 0,
                    "longitud": 6,
                    "activo": True,
                }
            )

        # ==========================
        # MÉTODOS DE PAGO
        # ==========================

        metodos = [
            ("Efectivo", False),
            ("Tarjeta débito", True),
            ("Tarjeta crédito", True),
            ("Transferencia", True),
            ("Nequi", True),
            ("Daviplata", True),
        ]

        for nombre, requiere in metodos:
            MetodoPago.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "requiere_referencia": requiere,
                    "activo": True,
                }
            )

        # ==========================
        # IMPUESTOS
        # ==========================

        impuestos = [
            ("IVA 19%", 19.00),
            ("IVA 5%", 5.00),
            ("Excluido", 0.00),
        ]

        for nombre, porcentaje in impuestos:
            Impuesto.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "porcentaje": porcentaje,
                    "activo": True,
                }
            )

        # ==========================
        # MOVIMIENTOS INVENTARIO
        # ==========================

        movimientos_inv = [
            ("Compra", "entrada"),
            ("Venta", "salida"),
            ("Ajuste entrada", "ajuste"),
            ("Ajuste salida", "ajuste"),
            ("Devolución cliente", "entrada"),
            ("Devolución proveedor", "salida"),
        ]

        for nombre, tipo in movimientos_inv:
            TipoMovimientoInventario.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "tipo": tipo,
                    "activo": True,
                }
            )

        # ==========================
        # MOVIMIENTOS CAJA
        # ==========================

        movimientos_caja = [
            ("Apertura caja", "entrada"),
            ("Venta", "entrada"),
            ("Gasto operativo", "salida"),
            ("Retiro", "salida"),
            ("Préstamo", "salida"),
            ("Ingreso extra", "entrada"),
        ]

        for nombre, tipo in movimientos_caja:
            TipoMovimientoCaja.objects.get_or_create(
                nombre=nombre,
                defaults={
                    "tipo": tipo,
                    "activo": True,
                }
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Datos iniciales cargados correctamente."
            )
        )

