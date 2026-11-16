from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Plataforma', {'fields': ('perfil',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Plataforma', {'fields': ('email', 'first_name', 'last_name', 'perfil')}),
    )
    list_display = ('username', 'email', 'perfil', 'is_staff')
