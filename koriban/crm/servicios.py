"""Lógica de negocio del CRM: asignación, cotizaciones, correos e historial."""
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.db.models import Count, Q
from django.urls import reverse
from django.utils import formats, timezone

from . import catalogos as cat
from .cotizador import calcular
from .models import (
    Actividad, CorreoEnviado, Cotizacion, Documento, ParametroCotizador, nombre_usuario,
)
from .pdf import generar_pdf_cotizacion


def registrar(prospecto, tipo, descripcion, usuario=None):
    return Actividad.objects.create(
        prospecto=prospecto, tipo=tipo, descripcion=descripcion[:300], usuario=usuario
    )


def fecha_larga(dt):
    return formats.date_format(timezone.localtime(dt), "j \\d\\e F \\d\\e Y")


def asignar_vendedor(prospecto, usuario=None):
    """Asigna al vendedor activo con menos prospectos abiertos (reparto equitativo)."""
    User = get_user_model()
    candidato = (
        User.objects.filter(is_active=True, perfil__rol="vendedor")
        .annotate(abiertos=Count("prospectos", filter=~Q(prospectos__etapa="mantenimiento")))
        .order_by("abiertos", "id")
        .first()
    )
    if candidato:
        prospecto.vendedor = candidato
        prospecto.save(update_fields=["vendedor"])
        registrar(prospecto, "asignacion", f"Asignado automáticamente a {nombre_usuario(candidato)}", usuario)
    return candidato


def cambiar_etapa(prospecto, etapa, usuario=None):
    if etapa == prospecto.etapa or etapa not in cat.ETAPAS_DICT:
        return False
    anterior = prospecto.get_etapa_display()
    prospecto.etapa = etapa
    prospecto.save(update_fields=["etapa", "actualizado"])
    registrar(prospecto, "etapa", f"Etapa: {anterior} → {prospecto.get_etapa_display()}", usuario)
    return True


def url_absoluta(path, request=None):
    if request is not None:
        return request.build_absolute_uri(path)
    return settings.SITE_URL.rstrip("/") + path


def generar_cotizacion(prospecto, usuario=None, fecha=None):
    """Calcula la propuesta, genera el PDF, lo guarda en los documentos del cliente."""
    resultado = calcular(prospecto.datos_cotizador(), ParametroCotizador.valores())
    ahora = fecha or timezone.now()
    folio = f"KOR-{timezone.localtime(ahora):%y%m%d}-{secrets.token_hex(2).upper()}"
    while Cotizacion.objects.filter(folio=folio).exists():
        folio = f"KOR-{timezone.localtime(ahora):%y%m%d}-{secrets.token_hex(2).upper()}"

    cotizacion = Cotizacion(
        prospecto=prospecto, folio=folio, paquete=resultado["paquete"], puntaje=resultado["puntaje"],
        precio=resultado["precio"], iva=resultado["iva"], total=resultado["total"],
        mantenimiento=resultado["mantenimiento"], vigencia_dias=resultado["vigencia_dias"],
        creado_por=usuario, creado=ahora,
        detalle={
            "desglose": resultado["desglose"], "observaciones": resultado["observaciones"],
            "anticipo": str(resultado["anticipo"]), "semanas": resultado["semanas"],
        },
    )

    info = {
        "folio": folio,
        "fecha": fecha_larga(ahora),
        "vence": fecha_larga(cotizacion.vence),
        "cliente": {
            "nombre": prospecto.nombre, "empresa": prospecto.empresa, "email": prospecto.email,
            "telefono": prospecto.telefono, "giro": prospecto.giro_texto, "alcaldia": prospecto.alcaldia,
        },
        "resultado": resultado,
        "vendedor": nombre_usuario(prospecto.vendedor) if prospecto.vendedor else "",
        "contacto": settings.KORIBAN,
    }
    pdf_bytes = generar_pdf_cotizacion(info)

    documento = Documento(
        prospecto=prospecto, nombre=f"Cotización {folio}", tipo="cotizacion",
        tamano=len(pdf_bytes), subido_por=usuario, creado=ahora,
    )
    documento.archivo.save(f"cotizacion_{folio}.pdf", ContentFile(pdf_bytes), save=False)
    documento.save()
    cotizacion.documento = documento
    cotizacion.save()

    prospecto.puntaje = resultado["puntaje"]
    prospecto.paquete_recomendado = resultado["paquete"]
    prospecto.valor_estimado = resultado["precio"]
    prospecto.save(update_fields=["puntaje", "paquete_recomendado", "valor_estimado", "actualizado"])
    registrar(prospecto, "cotizacion",
              f"Cotización {folio} generada: {resultado['paquete_nombre']} ({resultado['puntaje']} pts)",
              usuario)
    return cotizacion


def enviar_cotizacion(cotizacion, request=None, usuario=None):
    """Envía la propuesta por correo (simulado: se guarda en /correos_simulados)."""
    prospecto = cotizacion.prospecto
    enlace = url_absoluta(reverse("propuesta_pdf", args=[cotizacion.token]), request)
    pasos = "\n".join(f"  {i}. {p} — {d}" for i, (p, d) in enumerate(cat.SIGUIENTES_PASOS, 1))
    asunto = f"Tu propuesta Koriban {cotizacion.folio} — {cotizacion.get_paquete_display()}"
    cuerpo = (
        f"Hola {prospecto.nombre}:\n\n"
        f"Gracias por contarnos sobre tu negocio. Con base en tu diagnóstico te recomendamos el "
        f"Paquete {cotizacion.get_paquete_display()}.\n\n"
        f"Adjuntamos tu cotización en PDF (folio {cotizacion.folio}), vigente por "
        f"{cotizacion.vigencia_dias} días. También puedes consultarla aquí:\n{enlace}\n\n"
        f"Siguientes pasos:\n{pasos}\n\n"
        f"Tu asesor{' es ' + nombre_usuario(prospecto.vendedor) if prospecto.vendedor else ''} "
        f"te contactará pronto. Si prefieres, escríbenos por WhatsApp al {settings.KORIBAN['telefono']}.\n\n"
        f"Equipo Koriban\n{settings.KORIBAN['eslogan']}"
    )
    correo = EmailMessage(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [prospecto.email])
    if cotizacion.documento:
        with cotizacion.documento.archivo.open("rb") as f:
            correo.attach(f"Propuesta_{cotizacion.folio}.pdf", f.read(), "application/pdf")
    correo.send(fail_silently=True)

    registro = CorreoEnviado.objects.create(
        prospecto=prospecto, para=prospecto.email, asunto=asunto, cuerpo=cuerpo,
        adjunto=cotizacion.documento, simulado=True,
    )
    registrar(prospecto, "correo", f"Propuesta {cotizacion.folio} enviada a {prospecto.email} (simulado)", usuario)
    return registro


def mensaje_whatsapp(cotizacion, request=None):
    prospecto = cotizacion.prospecto
    enlace = url_absoluta(reverse("propuesta_pdf", args=[cotizacion.token]), request)
    return (
        f"Hola {prospecto.nombre}, te saluda el equipo de Koriban. Te compartimos tu propuesta "
        f"{cotizacion.folio} (Paquete {cotizacion.get_paquete_display()}): {enlace} "
        f"Siguientes pasos: firma de contrato, prototipado, implementación, pruebas, "
        f"capacitación y mantenimiento. ¿Agendamos una llamada?"
    )
