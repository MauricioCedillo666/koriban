from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from crm import views_publicas

urlpatterns = [
    # Sitio público (landing + cotizador)
    path("", views_publicas.landing, name="landing"),
    path("gracias/<uuid:token>/", views_publicas.gracias, name="gracias"),
    path("propuesta/<uuid:token>/", views_publicas.propuesta_pdf, name="propuesta_pdf"),
    # Autenticación (misma identidad visual que la landing)
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # CRM
    path("crm/", include("crm.urls")),
    # Panel técnico de Django (solo superusuario)
    path("admin/", admin.site.urls),
]
