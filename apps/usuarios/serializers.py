from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import Usuario, Rol, UsuarioRol


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ['id', 'nombre', 'descripcion', 'activo']


class UsuarioRolSerializer(serializers.ModelSerializer):
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    sede_nombre = serializers.CharField(source='sede.nombre', read_only=True)

    class Meta:
        model = UsuarioRol
        fields = ['id', 'rol', 'rol_nombre', 'sede', 'sede_nombre', 'activo']


class UsuarioListSerializer(serializers.ModelSerializer):
    """Vista resumida para listar usuarios."""
    roles = UsuarioRolSerializer(many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre_usuario', 'documento',
            'email', 'telefono', 'activo', 'roles',
            'fecha_creacion'
        ]


class UsuarioDetailSerializer(serializers.ModelSerializer):
    """Vista completa para crear y editar usuarios."""
    roles = UsuarioRolSerializer(many=True, read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=6)

    class Meta:
        model = Usuario
        fields = [
            'id', 'nombre_usuario', 'documento', 'email',
            'telefono', 'activo', 'roles', 'password',
            'fecha_creacion', 'fecha_actualizacion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_actualizacion']

    def validate_nombre_usuario(self, value):
        qs = Usuario.objects.filter(nombre_usuario=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este nombre de usuario ya está en uso.')
        return value

    def validate_documento(self, value):
        qs = Usuario.objects.filter(documento=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('Este documento ya está registrado.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        usuario = Usuario(**validated_data)
        if password:
            usuario.set_password(password)
        else:
            raise serializers.ValidationError({'password': 'La contraseña es obligatoria al crear un usuario.'})
        usuario.save()
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo = serializers.CharField(write_only=True, min_length=6)
    password_confirmacion = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password_nuevo'] != data['password_confirmacion']:
            raise serializers.ValidationError({'password_confirmacion': 'Las contraseñas no coinciden.'})
        return data


class AsignarRolSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioRol
        fields = ['usuario', 'rol', 'sede']