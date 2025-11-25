from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UsuarioManager(BaseUserManager):
    """Manager personalizado para el modelo Usuario."""
    
    def create_user(self, email, nombre, rut, password=None, **extra_fields):
        """Crea y guarda un usuario regular."""
        if not email:
            raise ValueError('El email es obligatorio')
        if not nombre:
            raise ValueError('El nombre es obligatorio')
        if not rut:
            raise ValueError('El RUT es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, rut=rut, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, nombre, rut, password=None, **extra_fields):
        """Crea y guarda un superusuario."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('rol', 'ADMIN')
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')
        
        return self.create_user(email, nombre, rut, password, **extra_fields)


class Usuario(AbstractUser):
    """Modelo personalizado de usuario."""
    
    class Rol(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        SUPERVISOR = 'SUPERVISOR', 'Supervisor'
        MECANICO = 'MECANICO', 'Mecánico'
        CHOFER = 'CHOFER', 'Chofer'
        GUARDIA = 'GUARDIA', 'Guardia'
        BODEGA = 'BODEGA', 'Bodega'
        EHS = 'EHS', 'EHS (Seguridad)'
    
    username = None  # Desactivar username
    email = models.EmailField('Correo electrónico', unique=True)
    nombre = models.CharField('Nombre completo', max_length=200)
    rut = models.CharField('RUT', max_length=12, unique=True)
    telefono = models.CharField('Teléfono', max_length=20, blank=True)
    rol = models.CharField('Rol', max_length=20, choices=Rol.choices, default=Rol.CHOFER)
    activo = models.BooleanField('Activo', default=True)
    fecha_creacion = models.DateTimeField('Fecha de creación', auto_now_add=True)
    
    objects = UsuarioManager()  # Asignar el manager personalizado
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre', 'rut']
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.get_rol_display()})"

    def save(self, *args, **kwargs):
        """Normalizar el rol a mayúsculas al guardar para mantener consistencia."""
        try:
            if self.rol:
                self.rol = str(self.rol).upper()
        except Exception:
            # Si por alguna razón rol no es settable, ignorar y proceder
            pass
        return super().save(*args, **kwargs)
