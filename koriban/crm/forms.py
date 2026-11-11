from datetime import timedelta

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Documento, Nota, Perfil, Prospecto, Tarea

FORMATO_DT = "%Y-%m-%dT%H:%M"


class CotizadorForm(forms.ModelForm):
    """Formulario público de la landing: recaba y categoriza la información del prospecto."""
    acepta_privacidad = forms.BooleanField(
        label="Acepto que Koriban use mis datos para enviarme esta propuesta.", required=True
    )

    class Meta:
        model = Prospecto
        fields = [
            "nombre", "empresa", "email", "telefono", "alcaldia",
            "giro", "giro_otro", "tamano", "usuarios_crm", "clientes_mes",
            "sitio_web", "usa_crm", "secciones", "necesita_whatsapp",
            "presupuesto", "urgencia", "comentarios",
        ]
        widgets = {
            "nombre": forms.TextInput(attrs={"placeholder": "Tu nombre", "autocomplete": "name"}),
            "empresa": forms.TextInput(attrs={"placeholder": "Nombre de tu negocio"}),
            "email": forms.EmailInput(attrs={"placeholder": "tucorreo@ejemplo.com", "autocomplete": "email"}),
            "telefono": forms.TextInput(attrs={"placeholder": "55 1234 5678", "autocomplete": "tel"}),
            "alcaldia": forms.TextInput(attrs={"placeholder": "Ej. Coyoacán, Naucalpan…"}),
            "giro_otro": forms.TextInput(attrs={"placeholder": "¿A qué se dedica tu negocio?"}),
            "comentarios": forms.Textarea(attrs={"rows": 3, "placeholder": "Cuéntanos qué te gustaría lograr (opcional)"}),
        }
        labels = {"necesita_whatsapp": "Quiero recibir y dar seguimiento a clientes por WhatsApp"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["telefono"].required = True

    def clean(self):
        datos = super().clean()
        if datos.get("giro") == "otro" and not datos.get("giro_otro"):
            self.add_error("giro_otro", "Cuéntanos a qué se dedica tu negocio.")
        return datos


class ProspectoForm(forms.ModelForm):
    """Alta / edición desde el CRM."""

    class Meta:
        model = Prospecto
        fields = [
            "nombre", "empresa", "email", "telefono", "alcaldia", "giro", "giro_otro", "tamano",
            "usuarios_crm", "clientes_mes", "sitio_web", "usa_crm", "secciones", "necesita_whatsapp",
            "presupuesto", "urgencia", "etapa", "vendedor", "comentarios",
        ]
        widgets = {"comentarios": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        if admin:
            self.fields["vendedor"].queryset = User.objects.filter(is_active=True).order_by("first_name")
            self.fields["vendedor"].label_from_instance = lambda u: u.get_full_name() or u.username
        else:
            del self.fields["vendedor"]


class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ["texto"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 2, "placeholder": "Escribe una nota sobre este cliente…"})}
        labels = {"texto": ""}


class TareaForm(forms.ModelForm):
    vence = forms.DateTimeField(
        label="Fecha y hora", input_formats=[FORMATO_DT],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=FORMATO_DT),
    )

    class Meta:
        model = Tarea
        fields = ["titulo", "prospecto", "asignado_a", "vence", "recurrencia", "cada_n_dias",
                  "repetir_hasta", "descripcion"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ej. Llamar para dar seguimiento a la propuesta"}),
            "repetir_hasta": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "descripcion": forms.Textarea(attrs={"rows": 2}),
            "cada_n_dias": forms.NumberInput(attrs={"min": 1, "max": 365}),
        }

    def __init__(self, *args, usuario=None, admin=False, prospectos=None, fijar_prospecto=False, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        if not self.initial.get("vence") and not self.instance.pk:
            manana = timezone.localtime() + timedelta(days=1)
            self.initial["vence"] = manana.replace(hour=10, minute=0, second=0, microsecond=0).strftime(FORMATO_DT)
        if admin:
            self.fields["asignado_a"].queryset = User.objects.filter(is_active=True)
            self.fields["asignado_a"].label_from_instance = lambda u: u.get_full_name() or u.username
            self.initial.setdefault("asignado_a", usuario.pk if usuario else None)
        else:
            del self.fields["asignado_a"]
        if fijar_prospecto:
            del self.fields["prospecto"]
        else:
            self.fields["prospecto"].queryset = prospectos if prospectos is not None else Prospecto.objects.none()
            self.fields["prospecto"].required = False
            self.fields["prospecto"].label = "Cliente (opcional)"
            self.fields["prospecto"].empty_label = "— Tarea general —"

    def clean(self):
        datos = super().clean()
        if datos.get("recurrencia") == "personalizada" and not datos.get("cada_n_dias"):
            self.add_error("cada_n_dias", "Indica cada cuántos días se repite.")
        hasta, vence = datos.get("repetir_hasta"), datos.get("vence")
        if hasta and vence and hasta < timezone.localtime(vence).date():
            self.add_error("repetir_hasta", "Debe ser posterior a la primera fecha.")
        return datos


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["prospecto", "nombre", "tipo", "archivo"]
        widgets = {"archivo": forms.ClearableFileInput(attrs={"accept": "application/pdf,.pdf"})}
        labels = {"prospecto": "Cliente", "nombre": "Nombre del documento", "archivo": "Archivo PDF"}

    def __init__(self, *args, prospectos=None, fijar_prospecto=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["nombre"].required = False
        if fijar_prospecto:
            del self.fields["prospecto"]
        else:
            self.fields["prospecto"].queryset = prospectos if prospectos is not None else Prospecto.objects.none()

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        limite = settings.DOCUMENTO_MAX_MB * 1024 * 1024
        if not archivo.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Solo se permiten archivos PDF.")
        if archivo.size > limite:
            raise forms.ValidationError(f"El archivo pesa más de {settings.DOCUMENTO_MAX_MB} MB.")
        inicio = archivo.read(5)
        archivo.seek(0)
        if inicio != b"%PDF-":
            raise forms.ValidationError("El archivo no es un PDF válido.")
        return archivo


class UsuarioForm(forms.Form):
    first_name = forms.CharField(label="Nombre", max_length=60)
    last_name = forms.CharField(label="Apellidos", max_length=80, required=False)
    username = forms.CharField(label="Usuario para iniciar sesión", max_length=40)
    email = forms.EmailField(label="Correo", required=False)
    rol = forms.ChoiceField(choices=Perfil.ROLES)
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput, min_length=8)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if get_user_model().objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("Ese usuario ya existe.")
        return username
