from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/buscar/", views.api_buscar, name="api_buscar"),
    path("clientes/", views.prospectos_lista, name="prospectos"),
    path("clientes/nuevo/", views.prospecto_nuevo, name="prospecto_nuevo"),
    path("clientes/<int:pk>/", views.prospecto_detalle, name="prospecto_detalle"),
    path("clientes/<int:pk>/editar/", views.prospecto_editar, name="prospecto_editar"),
    path("clientes/<int:pk>/etapa/", views.prospecto_etapa, name="prospecto_etapa"),
    path("clientes/<int:pk>/asignar/", views.prospecto_asignar, name="prospecto_asignar"),
    path("clientes/<int:pk>/eliminar/", views.prospecto_eliminar, name="prospecto_eliminar"),
    path("clientes/<int:pk>/nota/", views.nota_agregar, name="nota_agregar"),
    path("clientes/<int:pk>/tarea/", views.tarea_agregar, name="tarea_agregar"),
    path("clientes/<int:pk>/documento/", views.documento_subir, name="documento_subir"),
    path("clientes/<int:pk>/cotizar/", views.cotizacion_generar, name="cotizacion_generar"),
    path("clientes/<int:pk>/whatsapp/", views.whatsapp_registrar, name="whatsapp_registrar"),
    path("cotizaciones/<int:pk>/reenviar/", views.cotizacion_reenviar, name="cotizacion_reenviar"),
    path("embudo/", views.embudo, name="embudo"),
    path("tareas/", views.tareas, name="tareas"),
    path("tareas/<int:pk>/completar/", views.tarea_completar, name="tarea_completar"),
    path("tareas/<int:pk>/posponer/", views.tarea_posponer, name="tarea_posponer"),
    path("tareas/<int:pk>/eliminar/", views.tarea_eliminar, name="tarea_eliminar"),
    path("documentos/", views.documentos, name="documentos"),
    path("documentos/<int:pk>/", views.documento_ver, name="documento_ver"),
    path("documentos/<int:pk>/eliminar/", views.documento_eliminar, name="documento_eliminar"),
    path("correos/", views.correos, name="correos"),
    path("usuarios/", views.usuarios, name="usuarios"),
    path("usuarios/<int:pk>/activar/", views.usuario_activar, name="usuario_activar"),
    path("usuarios/<int:pk>/rol/", views.usuario_rol, name="usuario_rol"),
    path("configuracion/", views.configuracion, name="configuracion"),
]
