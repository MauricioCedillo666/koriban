import calendar
import re
import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from . import catalogos as cat
from .cotizador import PARAMETROS_DEFAULT

Usuario = settings.AUTH_USER_MODEL


class Perfil(models.Model):
    ROLES = [("admin", "Administrador"), ("vendedor", "Vendedor")]
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=10, choices=ROLES, default="vendedor")
    telefono = models.CharField(max_length=30, blank=True)

    class Meta:
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"{self.usuario} ({self.get_rol_display()})"


def es_admin(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perfil = getattr(user, "perfil", None)
    return bool(perfil and perfil.rol == "admin")


def nombre_usuario(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


class Prospecto(models.Model):
    ORIGENES = [("landing", "Landing page"), ("manual", "Captura manual")]
    PAQUETES = [("basico", "Básico"), ("profesional", "Profesional")]

    # Datos de contacto
    nombre = models.CharField("nombre de contacto", max_length=120)
    empresa = models.CharField("empresa o negocio", max_length=150, blank=True)
    email = models.EmailField("correo")
    telefono = models.CharField("teléfono / WhatsApp", max_length=30, blank=True)
    telefono_busqueda = models.CharField(max_length=30, blank=True, editable=False, db_index=True)
    alcaldia = models.CharField("alcaldía o municipio", max_length=100, blank=True)

    # Diagnóstico del negocio
    giro = models.CharField(max_length=40, choices=cat.GIROS, default="otro")
    giro_otro = models.CharField("especifica el giro", max_length=100, blank=True)
    tamano = models.CharField("tamaño del negocio", max_length=10, choices=cat.TAMANOS, default="micro")
    sitio_web = models.CharField("sitio web actual", max_length=12, choices=cat.SITIO_WEB, default="no")
    usa_crm = models.CharField("¿cómo gestiona hoy a sus clientes?", max_length=10, choices=cat.USA_CRM, default="no")
    clientes_mes = models.CharField("clientes o prospectos al mes", max_length=10, choices=cat.CLIENTES_MES, default="hasta_50")
    secciones = models.CharField("secciones del sitio", max_length=5, choices=cat.SECCIONES, default="1")
    necesita_whatsapp = models.BooleanField("necesita integración con WhatsApp", default=False)
    usuarios_crm = models.CharField("usuarios/empleados que usarán el CRM", max_length=5, choices=cat.USUARIOS_CRM, default="1")
    presupuesto = models.CharField(max_length=10, choices=cat.PRESUPUESTO, default="no_se")
    urgencia = models.CharField("¿para cuándo lo necesita?", max_length=12, choices=cat.URGENCIA, default="1_3")
    comentarios = models.TextField("comentarios", blank=True)

    # CRM
    origen = models.CharField(max_length=10, choices=ORIGENES, default="landing")
    etapa = models.CharField(max_length=20, choices=cat.ETAPAS, default="nuevo", db_index=True)
    vendedor = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name="prospectos", verbose_name="vendedor asignado")
    puntaje = models.PositiveIntegerField(default=0)
    paquete_recomendado = models.CharField(max_length=12, choices=PAQUETES, blank=True)
    valor_estimado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.nombre}" + (f" ({self.empresa})" if self.empresa else "")

    def save(self, *args, **kwargs):
        self.telefono_busqueda = re.sub(r"\D", "", self.telefono or "")
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("crm:prospecto_detalle", args=[self.pk])

    @property
    def giro_texto(self):
        if self.giro == "otro" and self.giro_otro:
            return f"Otro: {self.giro_otro}"
        return self.get_giro_display()

    @property
    def es_cliente(self):
        return self.etapa in cat.ETAPAS_CLIENTE

    @property
    def etapa_numero(self):
        return [e[0] for e in cat.ETAPAS].index(self.etapa) + 1

    @property
    def iniciales(self):
        partes = (self.nombre or "?").split()
        return "".join(p[0] for p in partes[:2]).upper()

    def datos_cotizador(self):
        return {
            "secciones": self.secciones, "necesita_whatsapp": self.necesita_whatsapp,
            "clientes_mes": self.clientes_mes, "usuarios_crm": self.usuarios_crm,
            "usa_crm": self.usa_crm, "sitio_web": self.sitio_web,
            "giro": self.giro, "presupuesto": self.presupuesto,
        }

    @property
    def whatsapp_numero(self):
        digitos = self.telefono_busqueda
        if len(digitos) == 10:  # número mexicano sin lada internacional
            return "52" + digitos
        return digitos


def ruta_documento(instance, filename):
    return f"documentos/prospecto_{instance.prospecto_id}/{filename}"


class Documento(models.Model):
    TIPOS = [
        ("cotizacion", "Cotización"), ("propuesta", "Propuesta"), ("contrato", "Contrato"),
        ("factura", "Factura"), ("otro", "Otro"),
    ]
    prospecto = models.ForeignKey(Prospecto, on_delete=models.CASCADE, related_name="documentos")
    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=12, choices=TIPOS, default="otro")
    archivo = models.FileField(upload_to=ruta_documento)
    tamano = models.PositiveIntegerField(default=0)
    subido_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return self.nombre

    @property
    def tamano_kb(self):
        return max(1, round(self.tamano / 1024))


class Cotizacion(models.Model):
    prospecto = models.ForeignKey(Prospecto, on_delete=models.CASCADE, related_name="cotizaciones")
    folio = models.CharField(max_length=30, unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    paquete = models.CharField(max_length=12, choices=Prospecto.PAQUETES)
    puntaje = models.PositiveIntegerField(default=0)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    iva = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    mantenimiento = models.DecimalField(max_digits=10, decimal_places=2)
    vigencia_dias = models.PositiveIntegerField(default=15)
    detalle = models.JSONField(default=dict)
    documento = models.OneToOneField(Documento, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="cotizacion")
    creado_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado"]
        verbose_name_plural = "cotizaciones"

    def __str__(self):
        return self.folio

    @property
    def vence(self):
        return self.creado + timedelta(days=self.vigencia_dias)

    @property
    def vigente(self):
        return timezone.now() <= self.vence


class Nota(models.Model):
    prospecto = models.ForeignKey(Prospecto, on_delete=models.CASCADE, related_name="notas")
    autor = models.ForeignKey(Usuario, null=True, on_delete=models.SET_NULL)
    texto = models.TextField()
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado"]


class Actividad(models.Model):
    """Historial del prospecto (se registra automáticamente)."""
    TIPOS = [
        ("creacion", "Alta"), ("etapa", "Cambio de etapa"), ("nota", "Nota"), ("tarea", "Tarea"),
        ("documento", "Documento"), ("correo", "Correo"), ("cotizacion", "Cotización"),
        ("asignacion", "Asignación"), ("edicion", "Edición"), ("whatsapp", "WhatsApp"),
    ]
    prospecto = models.ForeignKey(Prospecto, on_delete=models.CASCADE, related_name="actividades")
    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    tipo = models.CharField(max_length=12, choices=TIPOS)
    descripcion = models.CharField(max_length=300)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado"]
        verbose_name_plural = "actividades"


def _sumar_mes(fecha, meses=1):
    mes = fecha.month - 1 + meses
    anio = fecha.year + mes // 12
    mes = mes % 12 + 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return fecha.replace(year=anio, month=mes, day=dia)


class Tarea(models.Model):
    """Tarea o recordatorio de seguimiento, con recurrencia configurable."""
    prospecto = models.ForeignKey(Prospecto, null=True, blank=True, on_delete=models.CASCADE,
                                  related_name="tareas")
    asignado_a = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="tareas",
                                   verbose_name="responsable")
    creado_por = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="tareas_creadas")
    titulo = models.CharField("tarea o recordatorio", max_length=150)
    descripcion = models.TextField("detalle", blank=True)
    vence = models.DateTimeField("fecha y hora")
    recurrencia = models.CharField("repetir", max_length=15, choices=cat.RECURRENCIAS, default="ninguna")
    cada_n_dias = models.PositiveIntegerField("cada cuántos días", default=3)
    repetir_hasta = models.DateField("repetir hasta (opcional)", null=True, blank=True)
    completada = models.BooleanField(default=False)
    completada_en = models.DateTimeField(null=True, blank=True)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["completada", "vence"]

    def __str__(self):
        return self.titulo

    @property
    def vencida(self):
        return not self.completada and self.vence < timezone.now()

    @property
    def es_hoy(self):
        return not self.completada and timezone.localtime(self.vence).date() == timezone.localdate()

    @property
    def es_recurrente(self):
        return self.recurrencia != "ninguna"

    @property
    def recurrencia_texto(self):
        if self.recurrencia == "personalizada":
            return f"Cada {self.cada_n_dias} días"
        return self.get_recurrencia_display()

    def siguiente_fecha(self):
        f = self.vence
        r = self.recurrencia
        if r == "diaria":
            return f + timedelta(days=1)
        if r == "habiles":
            f = f + timedelta(days=1)
            while f.weekday() >= 5:
                f += timedelta(days=1)
            return f
        if r == "semanal":
            return f + timedelta(weeks=1)
        if r == "quincenal":
            return f + timedelta(weeks=2)
        if r == "mensual":
            return _sumar_mes(f)
        if r == "personalizada":
            return f + timedelta(days=max(1, self.cada_n_dias))
        return None

    def completar(self):
        """Marca como hecha. Si es recurrente, crea la siguiente ocurrencia."""
        self.completada = True
        self.completada_en = timezone.now()
        self.save(update_fields=["completada", "completada_en"])
        siguiente = self.siguiente_fecha()
        if not siguiente:
            return None
        # Si la tarea ya estaba atrasada, la siguiente no debe nacer atrasada
        ahora = timezone.now()
        copia = Tarea(vence=siguiente, recurrencia=self.recurrencia, cada_n_dias=self.cada_n_dias)
        while copia.vence < ahora:
            copia.vence = copia.siguiente_fecha()
        if self.repetir_hasta and timezone.localtime(copia.vence).date() > self.repetir_hasta:
            return None
        return Tarea.objects.create(
            prospecto=self.prospecto, asignado_a=self.asignado_a, creado_por=self.creado_por,
            titulo=self.titulo, descripcion=self.descripcion, vence=copia.vence,
            recurrencia=self.recurrencia, cada_n_dias=self.cada_n_dias,
            repetir_hasta=self.repetir_hasta,
        )


class CorreoEnviado(models.Model):
    """Bitácora de correos (en el prototipo el envío es simulado)."""
    prospecto = models.ForeignKey(Prospecto, null=True, blank=True, on_delete=models.SET_NULL,
                                  related_name="correos")
    para = models.EmailField()
    asunto = models.CharField(max_length=200)
    cuerpo = models.TextField()
    adjunto = models.ForeignKey(Documento, null=True, blank=True, on_delete=models.SET_NULL)
    simulado = models.BooleanField(default=True)
    enviado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-enviado"]
        verbose_name_plural = "correos enviados"


class ParametroCotizador(models.Model):
    clave = models.CharField(max_length=40, unique=True)
    nombre = models.CharField(max_length=120)
    grupo = models.CharField(max_length=40)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["orden"]
        verbose_name = "parámetro del cotizador"
        verbose_name_plural = "parámetros del cotizador"

    def __str__(self):
        return self.nombre

    @classmethod
    def asegurar(cls):
        """Crea los parámetros que falten con su valor por defecto."""
        existentes = set(cls.objects.values_list("clave", flat=True))
        nuevos = [
            cls(clave=c, nombre=n, valor=Decimal(str(v)), grupo=g, orden=i)
            for i, (c, n, v, g) in enumerate(PARAMETROS_DEFAULT) if c not in existentes
        ]
        if nuevos:
            cls.objects.bulk_create(nuevos)

    @classmethod
    def valores(cls):
        cls.asegurar()
        return {p.clave: p.valor for p in cls.objects.all()}
