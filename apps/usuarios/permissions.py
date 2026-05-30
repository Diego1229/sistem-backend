from rest_framework.permissions import BasePermission
from .models import UsuarioRol


def get_rol_activo(usuario, sede_id=None):
    """
    Retorna el nombre del rol activo del usuario.
    Si se pasa sede_id, filtra por esa sede específica.
    Retorna None si no tiene rol activo.
    """
    qs = UsuarioRol.objects.filter(
        usuario=usuario,
        activo=True
    ).select_related('rol')

    if sede_id:
        qs = qs.filter(sede_id=sede_id)

    ur = qs.first()
    return ur.rol.nombre if ur else None


def es_admin(usuario, sede_id=None):
    return get_rol_activo(usuario, sede_id) == 'admin'


def es_vendedor(usuario, sede_id=None):
    return get_rol_activo(usuario, sede_id) in ('admin', 'vendedor')


def get_sede_activa(usuario):
    """
    Retorna la sede donde el usuario tiene rol activo.
    Si tiene varios, retorna la primera.
    """
    ur = UsuarioRol.objects.filter(
        usuario=usuario,
        activo=True
    ).select_related('sede').first()
    return ur.sede if ur else None


class EsAdmin(BasePermission):
    """Solo administradores pueden acceder."""
    message = 'Solo los administradores pueden realizar esta acción.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and es_admin(request.user))


class EsAdminOVendedor(BasePermission):
    """Administradores y vendedores pueden acceder."""
    message = 'Debe ser administrador o vendedor para realizar esta acción.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and es_vendedor(request.user))