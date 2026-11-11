"""Catálogos de Koriban. Python puro (sin Django) para poder reutilizarse en el
cotizador, el generador de PDF y los modelos."""

GIROS = [
    ("inmobiliaria", "Inmobiliaria / bienes raíces"),
    ("salud", "Consultorio, clínica o salud"),
    ("restaurante", "Restaurante, cafetería o alimentos"),
    ("comercio", "Comercio minorista / tienda"),
    ("servicios_profesionales", "Servicios profesionales (contable, legal, consultoría)"),
    ("educacion", "Educación, escuela o cursos"),
    ("belleza", "Belleza, bienestar o gimnasio"),
    ("construccion", "Construcción y remodelación"),
    ("automotriz", "Automotriz (taller, refacciones, agencia)"),
    ("turismo", "Turismo y hotelería"),
    ("manufactura", "Manufactura o industria"),
    ("logistica", "Logística y transporte"),
    ("seguros", "Seguros y servicios financieros"),
    ("otro", "Otro"),
]

TAMANOS = [
    ("micro", "Micro (1 a 10 empleados)"),
    ("pequena", "Pequeña (11 a 50 empleados)"),
    ("mediana", "Mediana (51 a 250 empleados)"),
]

SITIO_WEB = [
    ("no", "No tengo sitio web"),
    ("actualizar", "Tengo, pero necesito renovarlo"),
    ("bien", "Tengo y funciona bien"),
]

USA_CRM = [
    ("no", "No uso nada"),
    ("excel", "Excel, libreta o WhatsApp"),
    ("gratuito", "Un CRM gratuito"),
    ("pagado", "Un CRM de pago"),
]

CLIENTES_MES = [
    ("hasta_50", "Hasta 50"),
    ("50_200", "De 50 a 200"),
    ("mas_200", "Más de 200"),
]

SECCIONES = [
    ("1", "Una sola página (landing)"),
    ("2_3", "2 a 3 secciones"),
    ("4_5", "4 a 5 secciones"),
    ("6", "6 o más secciones"),
]

USUARIOS_CRM = [
    ("1", "1 usuario"),
    ("2_5", "2 a 5 usuarios"),
    ("6_10", "6 a 10 usuarios"),
    ("11", "11 o más usuarios"),
]

PRESUPUESTO = [
    ("menos_10", "Menos de $10,000"),
    ("10_20", "$10,000 a $20,000"),
    ("20_30", "$20,000 a $30,000"),
    ("mas_30", "Más de $30,000"),
    ("no_se", "Aún no lo sé"),
]

# Monto máximo aproximado de cada rango (para detectar si la propuesta lo rebasa)
PRESUPUESTO_TOPE = {"menos_10": 10000, "10_20": 20000, "20_30": 30000}

URGENCIA = [
    ("inmediata", "Lo antes posible (este mes)"),
    ("1_3", "En 1 a 3 meses"),
    ("explorando", "Solo estoy explorando"),
]

ETAPAS = [
    ("nuevo", "Nuevo prospecto"),
    ("contactado", "Contactado"),
    ("propuesta_enviada", "Propuesta enviada"),
    ("negociacion", "Negociación"),
    ("contrato_firmado", "Contrato firmado"),
    ("prototipado", "Prototipado"),
    ("implementacion", "Implementación"),
    ("pruebas", "Pruebas"),
    ("capacitacion", "Capacitación"),
    ("mantenimiento", "Mantenimiento"),
]
ETAPAS_DICT = dict(ETAPAS)
# A partir de esta etapa el prospecto ya es cliente
ETAPAS_CLIENTE = [
    "contrato_firmado", "prototipado", "implementacion", "pruebas", "capacitacion", "mantenimiento",
]

PAQUETES = {
    "basico": {
        "nombre": "Paquete Básico",
        "incluye": [
            "Landing page de una página, responsiva (celular, tableta y computadora)",
            "CRM gratuito configurado con tus etapas de venta",
            "Formulario de contacto conectado al CRM",
            "Dominio y certificado de seguridad configurados",
        ],
        "semanas": "2 a 3 semanas",
    },
    "profesional": {
        "nombre": "Paquete Profesional",
        "incluye": [
            "Sitio web de 3 a 5 secciones, responsivo",
            "CRM con embudo de ventas personalizado",
            "Integración con WhatsApp para captar y dar seguimiento a prospectos",
            "Formularios conectados al CRM con asignación automática",
            "Capacitación para tu equipo",
        ],
        "semanas": "4 a 6 semanas",
    },
}

MANTENIMIENTO_INCLUYE = "Hosting, soporte, ajustes y reportes mensuales"

# Módulos sugeridos según el giro (personalizan la propuesta)
MODULOS_GIRO = {
    "inmobiliaria": [
        "Catálogo de propiedades con ficha, fotos y ubicación",
        "Seguimiento de interesados por inmueble",
        "Recordatorios automáticos de visitas",
    ],
    "salud": [
        "Agenda de citas en línea",
        "Registro básico de pacientes con aviso de privacidad",
        "Recordatorios de cita por WhatsApp",
    ],
    "restaurante": [
        "Menú digital y botón de pedidos por WhatsApp",
        "Base de clientes frecuentes para promociones",
        "Reservaciones en línea",
    ],
    "comercio": [
        "Catálogo de productos con botón de compra por WhatsApp",
        "Registro de clientes y compras recurrentes",
        "Campañas de promociones por segmento",
    ],
    "servicios_profesionales": [
        "Formulario de diagnóstico para nuevos clientes",
        "Seguimiento de expedientes o asuntos por cliente",
        "Agenda de reuniones y recordatorios",
    ],
    "educacion": [
        "Página de cursos y formulario de inscripción",
        "Seguimiento de aspirantes hasta su inscripción",
        "Recordatorios de pagos y fechas importantes",
    ],
    "belleza": [
        "Reservación de citas y servicios en línea",
        "Historial de servicios por cliente",
        "Recordatorios y promociones por WhatsApp",
    ],
    "construccion": [
        "Portafolio de obras y solicitud de cotización",
        "Seguimiento de cotizaciones por proyecto",
        "Registro de visitas técnicas",
    ],
    "automotriz": [
        "Solicitud de servicio o cita en línea",
        "Historial de servicios por vehículo",
        "Recordatorios de mantenimiento",
    ],
    "turismo": [
        "Galería de servicios y formulario de reservación",
        "Seguimiento de solicitudes por temporada",
        "Mensajes de confirmación y seguimiento",
    ],
    "manufactura": [
        "Catálogo de productos para clientes B2B",
        "Embudo de cotizaciones y pedidos",
        "Seguimiento de distribuidores",
    ],
    "logistica": [
        "Formulario de cotización de envíos",
        "Seguimiento de cuentas corporativas",
        "Recordatorios de renovación de contratos",
    ],
    "seguros": [
        "Formulario de cotización por tipo de seguro",
        "Seguimiento de pólizas y renovaciones",
        "Recordatorios de vencimiento por WhatsApp",
    ],
    "otro": [
        "Formulario de captación adaptado a tu servicio",
        "Embudo de ventas con tus propias etapas",
        "Recordatorios de seguimiento",
    ],
}

SIGUIENTES_PASOS = [
    ("Firma de contrato", "Formalizamos alcance, tiempos y forma de pago."),
    ("Prototipado", "Diseñamos una primera versión de tu sitio y tu CRM para validarla contigo."),
    ("Implementación", "Desarrollamos el sitio, configuramos el CRM y conectamos ambos."),
    ("Pruebas", "Verificamos formularios, integraciones y el flujo completo antes de publicar."),
    ("Capacitación", "Enseñamos a tu equipo a usar el CRM en su día a día."),
    ("Mantenimiento y mejoras", "Soporte, ajustes y reportes mensuales para seguir creciendo."),
]

RECURRENCIAS = [
    ("ninguna", "No se repite"),
    ("diaria", "Diaria"),
    ("habiles", "Días hábiles (lunes a viernes)"),
    ("semanal", "Semanal"),
    ("quincenal", "Cada 2 semanas"),
    ("mensual", "Mensual"),
    ("personalizada", "Cada N días"),
]
