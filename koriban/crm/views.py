import os
from datetime import datetime, time, timedelta
from functools import wraps
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import catalogos as cat
from . import servicios
from .cotizador import PARAMETROS_DEFAULT
from .forms import DocumentoForm, NotaForm, ProspectoForm, TareaForm, UsuarioForm
from .models import (
    Actividad, CorreoEnviado, Cotizacion, Documento, ParametroCotizador, Perfil, Prospecto, Tarea,
    es_admin, nombre_usuario,
)

# ---------------------------------------------------------------- utilidades


def solo_admin(vista):
    @wraps(vista)
    @login_required
    def envoltura(request, *args, **kwargs):
        if not es_admin(request.user):
            raise PermissionDenied("Solo administradores.")
        return vista(request, *args, **kwargs)
    return envoltura


def prospectos_visibles(user):
    """El administrador ve todo; el vendedor solo sus clientes asignados."""
    qs = Prospecto.objects.select_related("vendedor")
    return qs if es_admin(user) else qs.filter(vendedor=user)


def tareas_visibles(user):
    qs = Tarea.objects.select_related("prospecto", "asignado_a")
    return qs if es_admin(user) else qs.filter(asignado_a=user)


def obtener_prospecto(request, pk):
    return get_object_or_404(prospectos_visibles(request.user), pk=pk)


def es_ajax(request):
    return request.headers.get("x-requested-with") == "fetch"


def volver(request, por_defecto):
    destino = request.POST.get("next") or request.GET.get("next")
    if destino and destino.startswith("/"):
        return redirect(destino)
    return redirect(por_defecto)


def fin_de_hoy():
    return timezone.make_aware(datetime.combine(timezone.localdate(), time.max))


def inicio_de_hoy():
    return timezone.make_aware(datetime.combine(timezone.localdate(), time.min))


def buscar_en(qs, q):
    q = (q or "").strip()
    if not q:
        return qs
    filtro = Q(nombre__icontains=q) | Q(empresa__icontains=q) | Q(email__icontains=q)
    digitos = "".join(ch for ch in q if ch.isdigit())
    if len(digitos) >= 3:
        filtro |= Q(telefono_busqueda__contains=digitos)
    return qs.filter(filtro)


# ---------------------------------------------------------------- dashboard


@login_required
def dashboard(request):
    user = request.user
    qs = prospectos_visibles(user)
    total = qs.count()
    clientes = qs.filter(etapa__in=cat.ETAPAS_CLIENTE)
    n_clientes = clientes.count()
    inicio_mes = timezone.localdate().replace(day=1)

    por_etapa_raw = dict(qs.order_by().values_list("etapa").annotate(n=Count("id")))
    maximo = max(por_etapa_raw.values(), default=1) or 1
    por_etapa = [
        {"clave": c, "nombre": n, "n": por_etapa_raw.get(c, 0),
         "pct": round(por_etapa_raw.get(c, 0) * 100 / maximo)}
        for c, n in cat.ETAPAS
    ]
    giros_dict = dict(cat.GIROS)
    por_giro = [
        {"nombre": giros_dict.get(g, g), "n": n}
        for g, n in qs.order_by().values_list("giro").annotate(n=Count("id")).order_by("-n")[:6]
    ]

    mis_tareas = Tarea.objects.filter(asignado_a=user, completada=False).select_related("prospecto")
    contexto = {
        "total": total,
        "nuevos_mes": qs.filter(creado__date__gte=inicio_mes).count(),
        "n_clientes": n_clientes,
        "conversion": round(n_clientes * 100 / total) if total else 0,
        "en_negociacion": qs.filter(etapa__in=["propuesta_enviada", "negociacion"])
                            .aggregate(s=Sum("valor_estimado"))["s"] or 0,
        "ganado": clientes.aggregate(s=Sum("valor_estimado"))["s"] or 0,
        "por_etapa": por_etapa,
        "por_giro": por_giro,
        "tareas_vencidas": mis_tareas.filter(vence__lt=timezone.now()),
        "tareas_hoy": mis_tareas.filter(vence__gte=timezone.now(), vence__lte=fin_de_hoy()),
        "tareas_proximas": mis_tareas.filter(vence__gt=fin_de_hoy())[:5],
        "recientes": qs[:6],
        "actividad": Actividad.objects.filter(prospecto__in=qs).select_related("prospecto", "usuario")[:8],
    }
    return render(request, "crm/dashboard.html", contexto)


@login_required
@require_GET
def api_buscar(request):
    q = request.GET.get("q", "").strip()
    if len(q) < 2:
        return JsonResponse({"resultados": []})
    resultados = [
        {
            "id": p.pk, "nombre": p.nombre, "empresa": p.empresa, "email": p.email,
            "telefono": p.telefono, "etapa": p.get_etapa_display(), "url": p.get_absolute_url(),
        }
        for p in buscar_en(prospectos_visibles(request.user), q)[:8]
    ]
    return JsonResponse({"resultados": resultados})


# ---------------------------------------------------------------- prospectos


@login_required
def prospectos_lista(request):
    qs = buscar_en(prospectos_visibles(request.user), request.GET.get("q"))
    etapa = request.GET.get("etapa", "")
    giro = request.GET.get("giro", "")
    vendedor = request.GET.get("vendedor", "")
    if etapa == "clientes":
        qs = qs.filter(etapa__in=cat.ETAPAS_CLIENTE)
    elif etapa:
        qs = qs.filter(etapa=etapa)
    if giro:
        qs = qs.filter(giro=giro)
    if vendedor and es_admin(request.user):
        qs = qs.filter(vendedor_id=vendedor) if vendedor != "0" else qs.filter(vendedor__isnull=True)
    return render(request, "crm/prospectos_lista.html", {
        "prospectos": qs,
        "etapas": cat.ETAPAS,
        "giros": cat.GIROS,
        "vendedores": get_user_model().objects.filter(is_active=True) if es_admin(request.user) else [],
        "f": {"q": request.GET.get("q", ""), "etapa": etapa, "giro": giro, "vendedor": vendedor},
    })


@login_required
def prospecto_nuevo(request):
    admin = es_admin(request.user)
    form = ProspectoForm(request.POST or None, admin=admin, initial={"etapa": "nuevo"})
    if request.method == "POST" and form.is_valid():
        prospecto = form.save(commit=False)
        prospecto.origen = "manual"
        if not admin:
            prospecto.vendedor = request.user
        prospecto.save()
        servicios.registrar(prospecto, "creacion", "Prospecto capturado manualmente en el CRM", request.user)
        if admin and not prospecto.vendedor:
            servicios.asignar_vendedor(prospecto, request.user)
        if request.POST.get("generar_cotizacion"):
            cotizacion = servicios.generar_cotizacion(prospecto, request.user)
            if request.POST.get("enviar_correo"):
                servicios.enviar_cotizacion(cotizacion, request, request.user)
                servicios.cambiar_etapa(prospecto, "propuesta_enviada", request.user)
        messages.success(request, f"{prospecto.nombre} se agregó al CRM.")
        return redirect(prospecto)
    return render(request, "crm/prospecto_form.html", {"form": form, "nuevo": True})


@login_required
def prospecto_editar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    admin = es_admin(request.user)
    vendedor_antes = prospecto.vendedor_id
    etapa_antes = prospecto.etapa
    form = ProspectoForm(request.POST or None, instance=prospecto, admin=admin)
    if request.method == "POST" and form.is_valid():
        nueva_etapa = form.cleaned_data["etapa"]
        prospecto = form.save(commit=False)
        prospecto.etapa = etapa_antes
        prospecto.save()
        servicios.registrar(prospecto, "edicion", "Se actualizó la información del cliente", request.user)
        servicios.cambiar_etapa(prospecto, nueva_etapa, request.user)
        if admin and prospecto.vendedor_id != vendedor_antes:
            servicios.registrar(prospecto, "asignacion",
                                f"Reasignado a {nombre_usuario(prospecto.vendedor) or 'nadie'}", request.user)
        messages.success(request, "Cambios guardados.")
        return redirect(prospecto)
    return render(request, "crm/prospecto_form.html", {"form": form, "prospecto": prospecto, "nuevo": False})


@login_required
def prospecto_detalle(request, pk):
    prospecto = obtener_prospecto(request, pk)
    admin = es_admin(request.user)
    cotizacion = prospecto.cotizaciones.first()
    whatsapp_url = ""
    if cotizacion and prospecto.whatsapp_numero:
        texto = servicios.mensaje_whatsapp(cotizacion, request)
        whatsapp_url = f"https://wa.me/{prospecto.whatsapp_numero}?text={quote(texto)}"
    return render(request, "crm/prospecto_detalle.html", {
        "p": prospecto,
        "etapas": cat.ETAPAS,
        "nota_form": NotaForm(),
        "tarea_form": TareaForm(usuario=request.user, admin=admin, fijar_prospecto=True,
                                initial={"asignado_a": prospecto.vendedor_id or request.user.pk}),
        "doc_form": DocumentoForm(fijar_prospecto=True),
        "notas": prospecto.notas.select_related("autor"),
        "tareas": prospecto.tareas.select_related("asignado_a"),
        "documentos": prospecto.documentos.select_related("subido_por"),
        "cotizaciones": prospecto.cotizaciones.all(),
        "cotizacion": cotizacion,
        "actividades": prospecto.actividades.select_related("usuario")[:40],
        "correos": prospecto.correos.all()[:5],
        "whatsapp_url": whatsapp_url,
        "vendedores": get_user_model().objects.filter(is_active=True) if admin else [],
        "max_mb": settings.DOCUMENTO_MAX_MB,
        "giros_dict": dict(cat.GIROS),
    })


@login_required
@require_POST
def prospecto_etapa(request, pk):
    prospecto = obtener_prospecto(request, pk)
    etapa = request.POST.get("etapa")
    if etapa not in cat.ETAPAS_DICT:
        if es_ajax(request):
            return JsonResponse({"ok": False, "error": "Etapa inválida"}, status=400)
        messages.error(request, "Etapa inválida.")
        return redirect(prospecto)
    cambio = servicios.cambiar_etapa(prospecto, etapa, request.user)
    if es_ajax(request):
        return JsonResponse({"ok": True, "cambio": cambio, "etapa": prospecto.get_etapa_display()})
    if cambio:
        messages.success(request, f"Etapa actualizada a «{prospecto.get_etapa_display()}».")
    return volver(request, prospecto)


@solo_admin
@require_POST
def prospecto_asignar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    vendedor_id = request.POST.get("vendedor")
    vendedor = get_user_model().objects.filter(pk=vendedor_id, is_active=True).first() if vendedor_id else None
    prospecto.vendedor = vendedor
    prospecto.save(update_fields=["vendedor"])
    servicios.registrar(prospecto, "asignacion", f"Asignado a {nombre_usuario(vendedor) or 'nadie'}", request.user)
    messages.success(request, "Responsable actualizado.")
    return redirect(prospecto)


@solo_admin
@require_POST
def prospecto_eliminar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    for doc in prospecto.documentos.all():
        doc.archivo.delete(save=False)
    nombre = prospecto.nombre
    prospecto.delete()
    messages.success(request, f"Se eliminó a {nombre} y sus documentos.")
    return redirect("crm:prospectos")


@login_required
@require_POST
def nota_agregar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    form = NotaForm(request.POST)
    if form.is_valid():
        nota = form.save(commit=False)
        nota.prospecto = prospecto
        nota.autor = request.user
        nota.save()
        servicios.registrar(prospecto, "nota", f"Nota: {nota.texto[:120]}", request.user)
        messages.success(request, "Nota guardada.")
    return redirect(f"{prospecto.get_absolute_url()}#notas")


@login_required
@require_POST
def cotizacion_generar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    cotizacion = servicios.generar_cotizacion(prospecto, request.user)
    if request.POST.get("enviar"):
        servicios.enviar_cotizacion(cotizacion, request, request.user)
        if prospecto.etapa in ("nuevo", "contactado"):
            servicios.cambiar_etapa(prospecto, "propuesta_enviada", request.user)
        messages.success(request, f"Cotización {cotizacion.folio} generada y enviada por correo (simulado).")
    else:
        messages.success(request, f"Cotización {cotizacion.folio} generada.")
    return redirect(prospecto)


@login_required
@require_POST
def cotizacion_reenviar(request, pk):
    cotizacion = get_object_or_404(Cotizacion, pk=pk, prospecto__in=prospectos_visibles(request.user))
    servicios.enviar_cotizacion(cotizacion, request, request.user)
    messages.success(request, f"Propuesta {cotizacion.folio} reenviada a {cotizacion.prospecto.email} (simulado).")
    return redirect(cotizacion.prospecto)


@login_required
@require_POST
def whatsapp_registrar(request, pk):
    """Registra en el historial que se abrió WhatsApp con la propuesta."""
    prospecto = obtener_prospecto(request, pk)
    servicios.registrar(prospecto, "whatsapp", "Se abrió WhatsApp para enviar la propuesta", request.user)
    return JsonResponse({"ok": True})


# ---------------------------------------------------------------- embudo


@login_required
def embudo(request):
    qs = prospectos_visibles(request.user)
    columnas = [{"clave": c, "nombre": n, "items": []} for c, n in cat.ETAPAS]
    indice = {c["clave"]: c for c in columnas}
    for p in qs:
        indice[p.etapa]["items"].append(p)
    for c in columnas:
        c["total"] = sum(p.valor_estimado for p in c["items"])
    return render(request, "crm/embudo.html", {"columnas": columnas})


# ---------------------------------------------------------------- tareas


@login_required
def tareas(request):
    admin = es_admin(request.user)
    visibles = prospectos_visibles(request.user)
    form = TareaForm(request.POST or None, usuario=request.user, admin=admin, prospectos=visibles)
    if request.method == "POST":
        if form.is_valid():
            tarea = form.save(commit=False)
            if not admin:
                tarea.asignado_a = request.user
            tarea.creado_por = request.user
            tarea.save()
            if tarea.prospecto:
                servicios.registrar(tarea.prospecto, "tarea", f"Tarea creada: {tarea.titulo}", request.user)
            messages.success(request, "Tarea creada.")
            return redirect("crm:tareas")
        messages.error(request, "Revisa los datos de la tarea.")

    filtro = request.GET.get("ver", "pendientes")
    qs = tareas_visibles(request.user)
    if admin and request.GET.get("mias") == "1":
        qs = qs.filter(asignado_a=request.user)
    ahora = timezone.now()
    conteos = {
        "vencidas": qs.filter(completada=False, vence__lt=ahora).count(),
        "hoy": qs.filter(completada=False, vence__gte=ahora, vence__lte=fin_de_hoy()).count(),
        "proximas": qs.filter(completada=False, vence__gt=fin_de_hoy()).count(),
        "completadas": qs.filter(completada=True).count(),
    }
    conteos["pendientes"] = conteos["vencidas"] + conteos["hoy"] + conteos["proximas"]
    if filtro == "vencidas":
        qs = qs.filter(completada=False, vence__lt=ahora)
    elif filtro == "hoy":
        qs = qs.filter(completada=False, vence__gte=ahora, vence__lte=fin_de_hoy())
    elif filtro == "proximas":
        qs = qs.filter(completada=False, vence__gt=fin_de_hoy())
    elif filtro == "completadas":
        qs = qs.filter(completada=True).order_by("-completada_en")[:50]
    else:
        filtro = "pendientes"
        qs = qs.filter(completada=False)
    return render(request, "crm/tareas.html", {
        "tareas": qs, "form": form, "ver": filtro, "conteos": conteos,
        "mias": request.GET.get("mias") == "1",
    })


@login_required
@require_POST
def tarea_agregar(request, pk):
    prospecto = obtener_prospecto(request, pk)
    admin = es_admin(request.user)
    form = TareaForm(request.POST, usuario=request.user, admin=admin, fijar_prospecto=True)
    if form.is_valid():
        tarea = form.save(commit=False)
        tarea.prospecto = prospecto
        if not admin:
            tarea.asignado_a = request.user
        tarea.creado_por = request.user
        tarea.save()
        servicios.registrar(prospecto, "tarea",
                            f"Tarea creada: {tarea.titulo} ({tarea.recurrencia_texto})", request.user)
        messages.success(request, "Recordatorio programado.")
    else:
        errores = "; ".join(f"{k}: {', '.join(v)}" for k, v in form.errors.items())
        messages.error(request, f"No se pudo crear la tarea. {errores}")
    return redirect(f"{prospecto.get_absolute_url()}#tareas")


def _tarea_permitida(request, pk):
    tarea = get_object_or_404(Tarea, pk=pk)
    if not (es_admin(request.user) or tarea.asignado_a_id == request.user.pk):
        raise PermissionDenied
    return tarea


@login_required
@require_POST
def tarea_completar(request, pk):
    tarea = _tarea_permitida(request, pk)
    if tarea.completada:
        return volver(request, "crm:tareas")
    siguiente = tarea.completar()
    if tarea.prospecto:
        servicios.registrar(tarea.prospecto, "tarea", f"Tarea completada: {tarea.titulo}", request.user)
    if siguiente:
        fecha = timezone.localtime(siguiente.vence).strftime("%d/%m/%Y %H:%M")
        messages.success(request, f"¡Hecho! Próximo recordatorio: {fecha}.")
    else:
        messages.success(request, "¡Tarea completada!")
    return volver(request, "crm:tareas")


@login_required
@require_POST
def tarea_posponer(request, pk):
    tarea = _tarea_permitida(request, pk)
    dias = 1 if request.POST.get("cuanto") != "semana" else 7
    base = max(tarea.vence, timezone.now())
    tarea.vence = base + timedelta(days=dias)
    tarea.save(update_fields=["vence"])
    messages.success(request, "Recordatorio pospuesto.")
    return volver(request, "crm:tareas")


@login_required
@require_POST
def tarea_eliminar(request, pk):
    tarea = _tarea_permitida(request, pk)
    tarea.delete()
    messages.success(request, "Tarea eliminada.")
    return volver(request, "crm:tareas")


# ---------------------------------------------------------------- documentos


@login_required
def documentos(request):
    visibles = prospectos_visibles(request.user)
    if request.method == "POST":
        form = DocumentoForm(request.POST, request.FILES, prospectos=visibles)
        if form.is_valid():
            doc = _guardar_documento(form, request.user)
            messages.success(request, f"«{doc.nombre}» se guardó en el expediente de {doc.prospecto.nombre}.")
            return redirect("crm:documentos")
        messages.error(request, "No se pudo subir el documento.")
    else:
        form = DocumentoForm(prospectos=visibles, initial={"prospecto": request.GET.get("cliente")})

    qs = Documento.objects.filter(prospecto__in=visibles).select_related("prospecto", "subido_por")
    q = request.GET.get("q", "").strip()
    tipo = request.GET.get("tipo", "")
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(prospecto__nombre__icontains=q) | Q(prospecto__empresa__icontains=q))
    if tipo:
        qs = qs.filter(tipo=tipo)
    return render(request, "crm/documentos.html", {
        "documentos": qs, "form": form, "tipos": Documento.TIPOS, "f": {"q": q, "tipo": tipo},
    })


def _guardar_documento(form, user, prospecto=None):
    doc = form.save(commit=False)
    if prospecto:
        doc.prospecto = prospecto
    archivo = form.cleaned_data["archivo"]
    doc.tamano = archivo.size
    if not doc.nombre:
        doc.nombre = os.path.splitext(os.path.basename(archivo.name))[0][:150]
    doc.subido_por = user
    doc.save()
    servicios.registrar(doc.prospecto, "documento", f"Documento subido: {doc.nombre}", user)
    return doc


@login_required
@require_POST
def documento_subir(request, pk):
    prospecto = obtener_prospecto(request, pk)
    form = DocumentoForm(request.POST, request.FILES, fijar_prospecto=True)
    if form.is_valid():
        doc = _guardar_documento(form, request.user, prospecto)
        messages.success(request, f"«{doc.nombre}» guardado.")
    else:
        errores = " ".join(e for lista in form.errors.values() for e in lista)
        messages.error(request, f"No se pudo subir: {errores}")
    return redirect(f"{prospecto.get_absolute_url()}#documentos")


def _documento_permitido(request, pk):
    return get_object_or_404(
        Documento.objects.select_related("prospecto"), pk=pk,
        prospecto__in=prospectos_visibles(request.user),
    )


@login_required
def documento_ver(request, pk):
    doc = _documento_permitido(request, pk)
    descargar = request.GET.get("descargar") == "1"
    return FileResponse(doc.archivo.open("rb"), content_type="application/pdf",
                        as_attachment=descargar, filename=f"{doc.nombre}.pdf")


@solo_admin
@require_POST
def documento_eliminar(request, pk):
    doc = _documento_permitido(request, pk)
    prospecto = doc.prospecto
    nombre = doc.nombre
    doc.archivo.delete(save=False)
    doc.delete()
    servicios.registrar(prospecto, "documento", f"Documento eliminado: {nombre}", request.user)
    messages.success(request, f"Se eliminó «{nombre}».")
    return volver(request, "crm:documentos")


# ---------------------------------------------------------------- correos


@login_required
def correos(request):
    visibles = prospectos_visibles(request.user)
    qs = CorreoEnviado.objects.select_related("prospecto", "adjunto")
    if not es_admin(request.user):
        qs = qs.filter(prospecto__in=visibles)
    seleccionado = None
    if request.GET.get("id", "").isdigit():
        seleccionado = qs.filter(pk=request.GET["id"]).first()
    return render(request, "crm/correos.html", {
        "correos": qs[:100], "seleccionado": seleccionado or qs.first(),
    })


# ---------------------------------------------------------------- administración


@solo_admin
def usuarios(request):
    User = get_user_model()
    form = UsuarioForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        user = User.objects.create_user(
            username=d["username"], password=d["password"], email=d["email"],
            first_name=d["first_name"], last_name=d["last_name"],
        )
        Perfil.objects.create(usuario=user, rol=d["rol"])
        messages.success(request, f"Usuario «{user.username}» creado como {dict(Perfil.ROLES)[d['rol']]}.")
        return redirect("crm:usuarios")
    lista = (
        User.objects.select_related("perfil")
        .annotate(n_prospectos=Count("prospectos", distinct=True),
                  n_tareas=Count("tareas", filter=Q(tareas__completada=False), distinct=True))
        .order_by("-is_active", "first_name")
    )
    return render(request, "crm/usuarios.html", {"usuarios": lista, "form": form})


@solo_admin
@require_POST
def usuario_activar(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    if user == request.user:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
    else:
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        messages.success(request, f"«{user.username}» {'activado' if user.is_active else 'desactivado'}.")
    return redirect("crm:usuarios")


@solo_admin
@require_POST
def usuario_rol(request, pk):
    user = get_object_or_404(get_user_model(), pk=pk)
    rol = request.POST.get("rol")
    if rol in dict(Perfil.ROLES) and user != request.user:
        perfil, _ = Perfil.objects.get_or_create(usuario=user)
        perfil.rol = rol
        perfil.save()
        messages.success(request, f"Rol de «{user.username}» actualizado.")
    return redirect("crm:usuarios")


@solo_admin
def configuracion(request):
    ParametroCotizador.asegurar()
    parametros = list(ParametroCotizador.objects.all())
    if request.method == "POST":
        if request.POST.get("restablecer"):
            defaults = {c: v for c, _, v, _ in PARAMETROS_DEFAULT}
            for p in parametros:
                p.valor = defaults[p.clave]
                p.save(update_fields=["valor"])
            messages.success(request, "Se restablecieron los valores por defecto.")
            return redirect("crm:configuracion")
        errores = []
        for p in parametros:
            valor = request.POST.get(p.clave, "").strip()
            try:
                numero = float(valor)
                if numero < 0:
                    raise ValueError
            except ValueError:
                errores.append(p.nombre)
                continue
            p.valor = round(numero, 2)
            p.save(update_fields=["valor"])
        if errores:
            messages.error(request, "Valores inválidos en: " + ", ".join(errores))
        else:
            messages.success(request, "Configuración del cotizador guardada. Aplica a las nuevas cotizaciones.")
        return redirect("crm:configuracion")

    grupos = {}
    for p in parametros:
        grupos.setdefault(p.grupo, []).append(p)
    return render(request, "crm/configuracion.html", {"grupos": grupos})
