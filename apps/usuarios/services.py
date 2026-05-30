from django.utils import timezone
from .models import AudAcceso


def registrar_acceso(usuario, accion, request=None, sede=None):
    """
    Registra un evento de login/logout en aud_accesos.
    """
    ip = None
    user_agent = None

    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0] if x_forwarded else request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:300]

    AudAcceso.objects.create(
        usuario=usuario,
        sede=sede,
        ip=ip,
        user_agent=user_agent,
        accion=accion,
        activa=(accion == 'login'),
    )


def cerrar_sesion_activa(usuario):
    """
    Marca como inactiva la sesión abierta del usuario al hacer logout.
    """
    AudAcceso.objects.filter(
        usuario=usuario,
        accion='login',
        activa=True
    ).update(activa=False, fecha_fin=timezone.now())