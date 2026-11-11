from datetime import datetime, time

from django.conf import settings
from django.utils import timezone

from .models import Tarea, es_admin


def koriban(request):
    datos = {"KORIBAN": settings.KORIBAN, "es_admin": False, "recordatorios_pendientes": 0}
    user = getattr(request, "user", None)
    if user and user.is_authenticated and request.path.startswith("/crm"):
        fin_dia = timezone.make_aware(datetime.combine(timezone.localdate(), time.max))
        datos["es_admin"] = es_admin(user)
        datos["recordatorios_pendientes"] = Tarea.objects.filter(
            asignado_a=user, completada=False, vence__lte=fin_dia
        ).count()
    return datos
