from django.contrib import admin

from .models import (
    Actividad, CorreoEnviado, Cotizacion, Documento, Nota, ParametroCotizador, Perfil, Prospecto, Tarea,
)


@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "empresa", "giro", "etapa", "vendedor", "puntaje", "creado")
    list_filter = ("etapa", "giro", "origen")
    search_fields = ("nombre", "empresa", "email", "telefono")


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ("folio", "prospecto", "paquete", "total", "creado")


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "prospecto", "asignado_a", "vence", "recurrencia", "completada")
    list_filter = ("completada", "recurrencia")


admin.site.register([Perfil, Documento, Nota, Actividad, CorreoEnviado, ParametroCotizador])
admin.site.site_header = "Koriban · Panel técnico"
