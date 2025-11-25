from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('email', 'nombre', 'rol', 'activo')
    list_filter = ('rol', 'activo')
    search_fields = ('email', 'nombre', 'rut')
    ordering = ('nombre',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Info Personal', {'fields': ('nombre', 'rut', 'telefono')}),
        ('Permisos', {'fields': ('rol', 'activo', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nombre', 'rol', 'password1', 'password2'),
        }),
    )
