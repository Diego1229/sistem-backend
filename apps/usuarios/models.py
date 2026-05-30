from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from apps.configuracion.models import Sede


class UsuarioManager(BaseUserManager):
    def create_user(self, nombre_usuario, documento, password=None, **extra_fields):
        if not nombre_usuario:
            raise ValueError('El nombre de usuario es obligatorio')
        if not documento:
            raise ValueError('El documento es obligatorio')
        user = self.model(
            nombre_usuario=nombre_usuario,
            documento=documento,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, nombre_usuario, documento, password=None, **extra_fields):
        extra_fields.setdefault('activo', True)
        return self.create_user(nombre_usuario, documento, password, **extra_fields)


class Usuario(AbstractBaseUser):
    """
    Usuario del sistema. Reemplaza al User de Django.
    Se mapea a usr_usuarios. El password_hash lo maneja Django internamente.
    """
    nombre_usuario = models.CharField(max_length=80, unique=True)
    documento = models.CharField(max_length=20, unique=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    password_hash = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    # Django necesita saber cuál campo es el "password" real
    password = property(lambda self: self.password_hash)

    objects = UsuarioManager()

    USERNAME_FIELD = 'nombre_usuario'
    REQUIRED_FIELDS = ['documento']

    class Meta:
        db_table = 'usr_usuarios'
        managed = True

    def __str__(self):
        return self.nombre_usuario

    @property
    def is_active(self):
        return self.activo

    @property
    def is_staff(self):
        return False

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    def get_password(self):
        return self.password_hash

    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password_hash = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password as django_check
        def setter(raw):
            self.set_password(raw)
            self.save(update_fields=['password_hash'])
        return django_check(raw_password, self.password_hash, setter)


class Rol(models.Model):
    """Roles del sistema: admin, vendedor."""
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'usr_roles'
        managed = True
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class UsuarioRol(models.Model):
    """
    Relación usuario → rol → sede.
    Un usuario puede ser admin en sede A y vendedor en sede B.
    """
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='usuario_id',
        related_name='roles'
    )
    rol = models.ForeignKey(
        Rol,
        on_delete=models.PROTECT,
        db_column='id_rol',
        related_name='asignaciones'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.PROTECT,
        db_column='sede_id',
        related_name='usuarios_rol'
    )
    activo = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'usr_usuario_rol'
        managed = True       
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.usuario} — {self.rol} @ {self.sede}"


class AudAcceso(models.Model):
    """Registro de logins, logouts y acciones del sistema."""
    class Accion(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        ACCION = 'accion', 'Acción'

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='usuario_id',
        related_name='accesos'
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.SET_NULL,
        db_column='sede_id',
        null=True, blank=True,
        related_name='accesos'
    )
    ip = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.CharField(max_length=300, blank=True, null=True)
    accion = models.CharField(max_length=10, choices=Accion.choices, default=Accion.LOGIN)
    activa = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'aud_accesos'
        managed = True        
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.usuario} — {self.accion} @ {self.fecha_inicio}"