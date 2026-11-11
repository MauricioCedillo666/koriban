# Koriban — Prototipo de CRM, landing page y cotizador

Prototipo web para **Koriban**, una agencia (proyecto de seminario de titulación) que ofrece desarrollo web e implementación de CRM para PYMES, con nicho inicial en inmobiliarias y consultorios.

El sistema conecta una landing page pública con un CRM interno: los prospectos que cotizan en la página entran directamente al CRM para darles seguimiento.

## Funcionalidades

**Sitio público**
- Landing page de la agencia.
- Cotizador de paquetes (básico, intermedio y avanzado) que registra al prospecto automáticamente.

**CRM interno**
- Inicio de sesión con roles de **administrador** y **vendedor**.
- Dashboard con resumen de la operación.
- Gestión de prospectos y embudo de ventas por etapas.
- Tareas de seguimiento por prospecto.
- Generación de documentos en PDF: cotizaciones, contratos y reportes.
- Registro de correos (simulados en archivos para el entorno de prueba).
- Administración de usuarios y configuración.

## Tecnologías

- Python + Django
- SQLite
- HTML5, CSS3 y JavaScript
- ReportLab (generación de PDFs)
- Desarrollo asistido con Claude Code

## Cómo ejecutarlo

```bash
cd koriban
python -m venv .venv
.venv\Scripts\activate        # En Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py cargar_demo  # Opcional: carga datos de demostración
python manage.py runserver
```

Después abre http://127.0.0.1:8000 en el navegador.

## Autor

Mauricio Cedillo Villegas 
