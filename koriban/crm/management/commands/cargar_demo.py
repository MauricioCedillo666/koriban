"""Carga usuarios y 10 prospectos de ejemplo (uno por etapa del embudo).

Uso:
    python manage.py cargar_demo           # solo si la base está vacía
    python manage.py cargar_demo --reset   # borra todo y vuelve a cargar
"""
import shutil
from xml.sax.saxutils import escape
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from crm import servicios
from crm.models import (
    Actividad, CorreoEnviado, Documento, Nota, ParametroCotizador, Perfil, Prospecto, Tarea,
)
from crm.pdf import generar_pdf_simple

USUARIOS = [
    # usuario, contraseña, nombre, apellido, rol
    ("admin", "Koriban2026", "Admin", "Koriban", "admin"),
    ("laura", "Vendedor2026", "Laura", "Méndez", "vendedor"),
    ("carlos", "Vendedor2026", "Carlos", "Ruiz", "vendedor"),
]

# Un prospecto por cada etapa del embudo
PROSPECTOS = [
    dict(nombre="Fernanda Castillo", empresa="Boutique Fer", email="fernanda@ejemplo.com", telefono="55 3142 7781",
         alcaldia="Ecatepec", giro="comercio", tamano="micro", sitio_web="no", usa_crm="excel",
         clientes_mes="hasta_50", secciones="1", necesita_whatsapp=False, usuarios_crm="1",
         presupuesto="menos_10", urgencia="1_3", etapa="nuevo", origen="manual", dias=1, vendedor="laura",
         cotizar=False, comentarios="Nos contactó por Instagram. Vende ropa y quiere un catálogo sencillo."),
    dict(nombre="Luis Torres", empresa="Taller Automotriz Torres", email="luis.torres@ejemplo.com",
         telefono="55 2290 1144", alcaldia="Iztapalapa", giro="automotriz", tamano="micro", sitio_web="no",
         usa_crm="no", clientes_mes="50_200", secciones="2_3", necesita_whatsapp=False, usuarios_crm="2_5",
         presupuesto="10_20", urgencia="1_3", etapa="contactado", dias=4, vendedor="carlos",
         comentarios="Quiero que mis clientes agenden servicio desde internet."),
    dict(nombre="Jorge Martínez", empresa="Inmobiliaria Horizonte", email="jorge@ejemplo.com",
         telefono="55 5521 9087", alcaldia="Benito Juárez", giro="inmobiliaria", tamano="pequena",
         sitio_web="actualizar", usa_crm="excel", clientes_mes="50_200", secciones="4_5",
         necesita_whatsapp=True, usuarios_crm="6_10", presupuesto="20_30", urgencia="inmediata",
         etapa="propuesta_enviada", dias=6, vendedor="laura",
         comentarios="Tenemos 40 propiedades y perdemos interesados porque nadie les da seguimiento."),
    dict(nombre="Dra. Elena Ríos", empresa="Clínica Dental Ríos", email="elena.rios@ejemplo.com",
         telefono="55 1876 4410", alcaldia="Coyoacán", giro="salud", tamano="micro", sitio_web="no",
         usa_crm="no", clientes_mes="50_200", secciones="2_3", necesita_whatsapp=True, usuarios_crm="2_5",
         presupuesto="10_20", urgencia="inmediata", etapa="negociacion", dias=10, vendedor="carlos",
         comentarios="Necesito que mis pacientes agenden citas y reciban recordatorios."),
    dict(nombre="Ricardo Gómez", empresa="Despacho Gómez & Asociados", email="rgomez@ejemplo.com",
         telefono="55 6012 3398", alcaldia="Miguel Hidalgo", giro="servicios_profesionales", tamano="pequena",
         sitio_web="actualizar", usa_crm="gratuito", clientes_mes="hasta_50", secciones="4_5",
         necesita_whatsapp=False, usuarios_crm="6_10", presupuesto="20_30", urgencia="1_3",
         etapa="contrato_firmado", dias=15, vendedor="laura"),
    dict(nombre="Paola Sánchez", empresa="Colegio Montessori Arcoíris", email="direccion.arcoiris@ejemplo.com",
         telefono="55 4467 2209", alcaldia="Tlalpan", giro="educacion", tamano="pequena", sitio_web="no",
         usa_crm="excel", clientes_mes="50_200", secciones="4_5", necesita_whatsapp=True, usuarios_crm="2_5",
         presupuesto="20_30", urgencia="1_3", etapa="prototipado", dias=21, vendedor="carlos",
         comentarios="Queremos captar aspirantes para el próximo ciclo escolar."),
    dict(nombre="Mariana López", empresa="Estética Mariana", email="mariana.estetica@ejemplo.com",
         telefono="55 7731 5520", alcaldia="Naucalpan", giro="belleza", tamano="micro", sitio_web="no",
         usa_crm="no", clientes_mes="50_200", secciones="2_3", necesita_whatsapp=True, usuarios_crm="2_5",
         presupuesto="10_20", urgencia="inmediata", etapa="implementacion", dias=28, vendedor="laura"),
    dict(nombre="Héctor Flores", empresa="Construcciones Flores", email="hflores@ejemplo.com",
         telefono="55 2984 6613", alcaldia="Álvaro Obregón", giro="construccion", tamano="mediana",
         sitio_web="actualizar", usa_crm="excel", clientes_mes="hasta_50", secciones="6",
         necesita_whatsapp=True, usuarios_crm="11", presupuesto="mas_30", urgencia="1_3",
         etapa="pruebas", dias=40, vendedor="carlos"),
    dict(nombre="Sofía Hernández", empresa="Café La Molienda", email="sofia@ejemplo.com",
         telefono="55 3378 0091", alcaldia="Cuauhtémoc", giro="restaurante", tamano="micro", sitio_web="no",
         usa_crm="no", clientes_mes="mas_200", secciones="1", necesita_whatsapp=False, usuarios_crm="1",
         presupuesto="menos_10", urgencia="inmediata", etapa="capacitacion", dias=45, vendedor="laura"),
    dict(nombre="Andrés Ramírez", empresa="Ramírez Agentes de Seguros", email="andres.ramirez@ejemplo.com",
         telefono="55 8812 4456", alcaldia="Tlalnepantla", giro="seguros", tamano="pequena",
         sitio_web="actualizar", usa_crm="gratuito", clientes_mes="50_200", secciones="2_3",
         necesita_whatsapp=True, usuarios_crm="6_10", presupuesto="20_30", urgencia="1_3",
         etapa="mantenimiento", dias=70, vendedor="carlos"),
]

NOTAS = {
    "Luis Torres": ["Le interesa que el taller mande recordatorios de servicio cada 6 meses."],
    "Jorge Martínez": ["Pidió ver ejemplos de catálogos de propiedades.",
                       "Comparando con un partner de HubSpot; le preocupa el costo de licencias."],
    "Dra. Elena Ríos": ["Pidió dividir el pago en 3 exhibiciones. Revisar con administración.",
                        "Le gustó la agenda de citas en línea."],
    "Ricardo Gómez": ["Contrato firmado. Anticipo recibido por transferencia."],
    "Paola Sánchez": ["Prototipo presentado a la dirección; pidieron cambiar colores a los institucionales."],
    "Mariana López": ["Ya nos compartió logotipo y fotos del local."],
    "Héctor Flores": ["Pruebas del formulario de cotización de obra: todo correcto, falta probar WhatsApp."],
    "Sofía Hernández": ["Capacitación 1 de 2 completada con las dos encargadas."],
    "Andrés Ramírez": ["Enviado reporte mensual de octubre. Quiere agregar un cotizador de autos."],
}

TAREAS = [
    # prospecto, título, desplazamiento en horas desde ahora, recurrencia, cada_n_dias
    ("Fernanda Castillo", "Primera llamada de diagnóstico", 3, "ninguna", 3),
    ("Luis Torres", "Enviar cotización después de la visita al taller", -20, "ninguna", 3),
    ("Jorge Martínez", "Dar seguimiento a la propuesta enviada", 1, "personalizada", 3),
    ("Dra. Elena Ríos", "Llamar para cerrar la negociación", -26, "ninguna", 3),
    ("Ricardo Gómez", "Agendar reunión de arranque del proyecto", 30, "ninguna", 3),
    ("Paola Sánchez", "Junta semanal de avance con la dirección", 50, "semanal", 3),
    ("Mariana López", "Reporte diario de avance de implementación", 2, "habiles", 3),
    ("Héctor Flores", "Validar pruebas de integración con WhatsApp", 26, "ninguna", 3),
    ("Sofía Hernández", "Segunda sesión de capacitación", 74, "ninguna", 3),
    ("Andrés Ramírez", "Enviar reporte mensual de mantenimiento", 140, "mensual", 3),
]


class Command(BaseCommand):
    help = "Carga usuarios y datos de ejemplo para la demostración de Koriban."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Borra todos los datos antes de cargar.")

    def handle(self, *args, **opciones):
        User = get_user_model()
        if opciones["reset"]:
            call_command("flush", interactive=False, verbosity=0)
            for carpeta in ("media", "correos_simulados"):
                shutil.rmtree(settings.BASE_DIR / carpeta, ignore_errors=True)
            self.stdout.write("Base de datos reiniciada.")
        elif User.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya hay datos cargados. Usa --reset si quieres reiniciar la demo."))
            return

        with transaction.atomic():
            self._cargar()
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
        self.stdout.write("  Administrador: admin / Koriban2026")
        self.stdout.write("  Vendedores:    laura / Vendedor2026  ·  carlos / Vendedor2026")

    def _cargar(self):
        User = get_user_model()
        ParametroCotizador.asegurar()
        usuarios = {}
        for username, password, nombre, apellido, rol in USUARIOS:
            u = User.objects.create_user(
                username=username, password=password, first_name=nombre, last_name=apellido,
                email=f"{username}@koriban.mx", is_staff=(rol == "admin"), is_superuser=(rol == "admin"),
            )
            Perfil.objects.create(usuario=u, rol=rol)
            usuarios[username] = u

        ahora = timezone.now()
        prospectos = {}
        for datos in PROSPECTOS:
            datos = dict(datos)
            dias = datos.pop("dias")
            vendedor = usuarios[datos.pop("vendedor")]
            etapa_final = datos.pop("etapa")
            cotizar = datos.pop("cotizar", True)
            origen = datos.pop("origen", "landing")
            alta = ahora - timedelta(days=dias, hours=3)

            p = Prospecto.objects.create(**datos, origen=origen, etapa="nuevo", vendedor=vendedor, creado=alta)
            servicios.registrar(p, "creacion", "Prospecto registrado desde la landing page"
                                if origen == "landing" else "Prospecto capturado manualmente en el CRM")
            servicios.registrar(p, "asignacion", f"Asignado automáticamente a {vendedor.get_full_name()}")
            if cotizar:
                cot = servicios.generar_cotizacion(p, fecha=alta + timedelta(minutes=1))
                servicios.enviar_cotizacion(cot)
                servicios.cambiar_etapa(p, "propuesta_enviada")
            if etapa_final != p.etapa:
                servicios.cambiar_etapa(p, etapa_final, vendedor)

            if p.es_cliente:
                self._contrato(p, vendedor, alta + timedelta(days=min(dias - 1, 5)))
            if etapa_final == "mantenimiento":
                self._reporte(p, vendedor, ahora - timedelta(days=4))

            for texto in NOTAS.get(p.nombre, []):
                Nota.objects.create(prospecto=p, autor=vendedor, texto=texto,
                                    creado=alta + timedelta(days=max(dias - 2, 0)))
                servicios.registrar(p, "nota", f"Nota: {texto[:120]}", vendedor)

            # Escalonar fechas del historial para que se vea realista
            actividades = list(Actividad.objects.filter(prospecto=p).order_by("id"))
            paso = timedelta(hours=max(dias * 24 // max(len(actividades), 1), 1))
            for i, a in enumerate(actividades):
                Actividad.objects.filter(pk=a.pk).update(creado=alta + paso * i)
            CorreoEnviado.objects.filter(prospecto=p).update(enviado=alta + timedelta(minutes=2))
            prospectos[p.nombre] = p

        for nombre, titulo, horas, recurrencia, n in TAREAS:
            p = prospectos[nombre]
            Tarea.objects.create(
                prospecto=p, asignado_a=p.vendedor, creado_por=p.vendedor, titulo=titulo,
                vence=ahora + timedelta(hours=horas), recurrencia=recurrencia, cada_n_dias=n,
            )
        Tarea.objects.create(
            asignado_a=usuarios["admin"], creado_por=usuarios["admin"],
            titulo="Revisar el embudo y las metas de la semana",
            vence=ahora + timedelta(hours=1), recurrencia="semanal",
        )
        Tarea.objects.create(
            prospecto=prospectos["Ricardo Gómez"], asignado_a=usuarios["laura"], creado_por=usuarios["laura"],
            titulo="Enviar contrato firmado escaneado", vence=ahora - timedelta(days=3),
            completada=True, completada_en=ahora - timedelta(days=3),
        )

    def _pdf_documento(self, p, vendedor, nombre, tipo, pdf_bytes, fecha, archivo):
        doc = Documento(prospecto=p, nombre=nombre, tipo=tipo, tamano=len(pdf_bytes),
                        subido_por=vendedor, creado=fecha)
        doc.archivo.save(archivo, ContentFile(pdf_bytes), save=False)
        doc.save()
        servicios.registrar(p, "documento", f"Documento subido: {nombre}", vendedor)

    def _contrato(self, p, vendedor, fecha):
        cot = p.cotizaciones.first()
        pdf = generar_pdf_simple(
            "Contrato de prestación de servicios",
            f"{p.empresa} · Documento de ejemplo generado para la demostración",
            [
                f"<b>Cliente:</b> {escape(p.nombre)} ({escape(p.empresa)}).",
                f"<b>Servicio:</b> Paquete {cot.get_paquete_display() if cot else ''} de Koriban: diseño, "
                "implementación e integración de sitio web con CRM.",
                f"<b>Inversión:</b> ${cot.total:,.2f} MXN con IVA incluido; 50% de anticipo a la firma y "
                "50% a la entrega." if cot else "",
                "<b>Etapas:</b> prototipado, implementación, pruebas, capacitación y mantenimiento.",
                "Este documento es un ejemplo sin validez legal, creado para mostrar el módulo de documentos.",
            ],
            settings.KORIBAN, folio=cot.folio if cot else "",
        )
        self._pdf_documento(p, vendedor, f"Contrato firmado — {p.empresa}", "contrato", pdf, fecha,
                            f"contrato_{p.pk}.pdf")

    def _reporte(self, p, vendedor, fecha):
        pdf = generar_pdf_simple(
            "Reporte mensual de mantenimiento",
            f"{p.empresa} · Octubre 2026 (ejemplo)",
            [
                "<b>Disponibilidad del sitio:</b> 99.9%.",
                "<b>Prospectos captados por el sitio:</b> 64 (31 por WhatsApp).",
                "<b>Ajustes realizados:</b> nuevo formulario de cotización de seguro de gastos médicos.",
                "<b>Recomendación:</b> agregar un cotizador de seguros de auto en la página principal.",
            ],
            settings.KORIBAN,
        )
        self._pdf_documento(p, vendedor, "Reporte mensual — octubre", "otro", pdf, fecha, f"reporte_{p.pk}.pdf")
