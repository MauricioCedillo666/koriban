from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from . import catalogos as cat
from . import servicios
from .forms import CotizadorForm
from .models import Cotizacion


def landing(request):
    if request.method == "POST":
        form = CotizadorForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                prospecto = form.save(commit=False)
                prospecto.origen = "landing"
                prospecto.etapa = "nuevo"
                prospecto.save()
                servicios.registrar(prospecto, "creacion", "Prospecto registrado desde la landing page")
                servicios.asignar_vendedor(prospecto)
                cotizacion = servicios.generar_cotizacion(prospecto)
            servicios.enviar_cotizacion(cotizacion, request=request)
            servicios.cambiar_etapa(prospecto, "propuesta_enviada")
            return redirect("gracias", token=cotizacion.token)
        messages.error(request, "Revisa los campos marcados para poder generar tu propuesta.")
    else:
        form = CotizadorForm()

    contexto = {
        "form": form,
        "giros": cat.GIROS[:-1],
        "pasos": cat.SIGUIENTES_PASOS,
        "paquetes": cat.PAQUETES,
        "mantenimiento_incluye": cat.MANTENIMIENTO_INCLUYE,
        "con_errores": request.method == "POST",
    }
    return render(request, "publico/landing.html", contexto)


def gracias(request, token):
    cotizacion = get_object_or_404(Cotizacion.objects.select_related("prospecto"), token=token)
    return render(request, "publico/gracias.html", {
        "cotizacion": cotizacion,
        "prospecto": cotizacion.prospecto,
        "pasos": cat.SIGUIENTES_PASOS,
        "pdf_url": reverse("propuesta_pdf", args=[token]),
    })


def propuesta_pdf(request, token):
    """Enlace privado (por token) que recibe el prospecto en su correo."""
    cotizacion = get_object_or_404(Cotizacion, token=token)
    if not cotizacion.documento or not cotizacion.documento.archivo:
        raise Http404
    return FileResponse(
        cotizacion.documento.archivo.open("rb"),
        content_type="application/pdf",
        filename=f"Propuesta_{cotizacion.folio}.pdf",
        as_attachment=request.GET.get("descargar") == "1",
    )
