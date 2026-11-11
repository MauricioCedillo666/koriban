from django import template

register = template.Library()

COLORES_ETAPA = {
    "nuevo": "e-nuevo", "contactado": "e-contactado", "propuesta_enviada": "e-propuesta",
    "negociacion": "e-negociacion", "contrato_firmado": "e-cliente", "prototipado": "e-cliente",
    "implementacion": "e-cliente", "pruebas": "e-cliente", "capacitacion": "e-cliente",
    "mantenimiento": "e-mantenimiento",
}


@register.filter
def moneda(valor):
    try:
        return "${:,.2f}".format(float(valor))
    except (TypeError, ValueError):
        return "$0.00"


@register.filter
def moneda_corta(valor):
    try:
        return "${:,.0f}".format(float(valor))
    except (TypeError, ValueError):
        return "$0"


@register.filter
def clase_etapa(etapa):
    return COLORES_ETAPA.get(etapa, "e-nuevo")


@register.filter
def nombre(user):
    if not user:
        return "Sin asignar"
    return user.get_full_name() or user.username


@register.filter
def get(diccionario, clave):
    try:
        return diccionario.get(clave)
    except AttributeError:
        return None
