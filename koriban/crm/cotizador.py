"""Motor de cotización por puntos de Koriban.

Python puro (sin Django): recibe las respuestas del formulario y los
parámetros configurables, y devuelve el paquete recomendado, el desglose
de puntos y los precios. Los parámetros se editan desde
CRM > Configuración (solo administradores).
"""
from decimal import ROUND_HALF_UP, Decimal

from . import catalogos as cat

# (clave, nombre visible, valor por defecto, grupo)
PARAMETROS_DEFAULT = [
    ("pts_secciones_1", "Secciones: una página", 0, "Puntos"),
    ("pts_secciones_2_3", "Secciones: 2 a 3", 2, "Puntos"),
    ("pts_secciones_4_5", "Secciones: 4 a 5", 4, "Puntos"),
    ("pts_secciones_6", "Secciones: 6 o más", 6, "Puntos"),
    ("pts_whatsapp", "Necesita integración con WhatsApp", 3, "Puntos"),
    ("pts_clientes_hasta_50", "Clientes al mes: hasta 50", 0, "Puntos"),
    ("pts_clientes_50_200", "Clientes al mes: 50 a 200", 2, "Puntos"),
    ("pts_clientes_mas_200", "Clientes al mes: más de 200", 4, "Puntos"),
    ("pts_usuarios_1", "Usuarios del CRM: 1", 0, "Puntos"),
    ("pts_usuarios_2_5", "Usuarios del CRM: 2 a 5", 2, "Puntos"),
    ("pts_usuarios_6_10", "Usuarios del CRM: 6 a 10", 3, "Puntos"),
    ("pts_usuarios_11", "Usuarios del CRM: 11 o más", 5, "Puntos"),
    ("pts_sin_crm", "No usa CRM (o usa Excel/libreta)", 1, "Puntos"),
    ("pts_sin_sitio", "No tiene sitio o necesita renovarlo", 1, "Puntos"),
    ("umbral_profesional", "Puntos mínimos para recomendar Profesional", 5, "Reglas"),
    ("basico_base", "Básico: precio base", 8000, "Precios (MXN)"),
    ("basico_por_punto", "Básico: aumento por punto", 800, "Precios (MXN)"),
    ("basico_max", "Básico: precio máximo", 12000, "Precios (MXN)"),
    ("profesional_base", "Profesional: precio base", 15000, "Precios (MXN)"),
    ("profesional_por_punto", "Profesional: aumento por punto sobre el umbral", 1000, "Precios (MXN)"),
    ("profesional_max", "Profesional: precio máximo", 25000, "Precios (MXN)"),
    ("mant_base", "Mantenimiento: mensualidad base", 800, "Precios (MXN)"),
    ("mant_por_punto", "Mantenimiento: aumento por punto", 150, "Precios (MXN)"),
    ("mant_max", "Mantenimiento: mensualidad máxima", 2500, "Precios (MXN)"),
    ("iva_pct", "IVA (%)", 16, "Condiciones"),
    ("anticipo_pct", "Anticipo al firmar (%)", 50, "Condiciones"),
    ("vigencia_dias", "Vigencia de la cotización (días)", 15, "Condiciones"),
]

DEFAULTS = {clave: Decimal(str(valor)) for clave, _, valor, _ in PARAMETROS_DEFAULT}

DOS = Decimal("0.01")


def _d(valor):
    return Decimal(str(valor)).quantize(DOS, rounding=ROUND_HALF_UP)


def calcular(datos, params=None):
    """Calcula la propuesta.

    datos: dict con las claves secciones, necesita_whatsapp, clientes_mes,
           usuarios_crm, usa_crm, sitio_web, giro, presupuesto.
    params: dict clave -> Decimal (si falta alguna, se usa el valor por defecto).
    """
    p = dict(DEFAULTS)
    if params:
        p.update({k: Decimal(str(v)) for k, v in params.items()})

    desglose = []

    def sumar(concepto, clave):
        pts = int(p[clave])
        desglose.append({"concepto": concepto, "puntos": pts})
        return pts

    secciones = datos.get("secciones", "1")
    puntos = sumar(f"Secciones del sitio: {dict(cat.SECCIONES).get(secciones, secciones)}",
                   f"pts_secciones_{secciones}")

    if datos.get("necesita_whatsapp"):
        puntos += sumar("Integración con WhatsApp", "pts_whatsapp")

    clientes = datos.get("clientes_mes", "hasta_50")
    puntos += sumar(f"Clientes al mes: {dict(cat.CLIENTES_MES).get(clientes, clientes)}",
                    f"pts_clientes_{clientes}")

    usuarios = datos.get("usuarios_crm", "1")
    puntos += sumar(f"Usuarios del CRM: {dict(cat.USUARIOS_CRM).get(usuarios, usuarios)}",
                    f"pts_usuarios_{usuarios}")

    if datos.get("usa_crm") in ("no", "excel"):
        puntos += sumar("Configuración de CRM desde cero", "pts_sin_crm")

    if datos.get("sitio_web") in ("no", "actualizar"):
        puntos += sumar("Sitio web nuevo o renovado", "pts_sin_sitio")

    umbral = int(p["umbral_profesional"])
    # WhatsApp y más de 3 secciones solo existen en el Profesional
    requiere_profesional = datos.get("necesita_whatsapp") or secciones in ("4_5", "6")
    paquete = "profesional" if (puntos >= umbral or requiere_profesional) else "basico"

    if paquete == "basico":
        precio = p["basico_base"] + puntos * p["basico_por_punto"]
        precio = min(precio, p["basico_max"])
    else:
        extra = max(puntos - umbral, 0)
        precio = p["profesional_base"] + extra * p["profesional_por_punto"]
        precio = min(precio, p["profesional_max"])

    mant = min(p["mant_base"] + puntos * p["mant_por_punto"], p["mant_max"])

    precio = _d(precio)
    iva = _d(precio * p["iva_pct"] / 100)
    total = _d(precio + iva)
    anticipo = _d(total * p["anticipo_pct"] / 100)
    mant = _d(mant)
    mant_iva = _d(mant * (1 + p["iva_pct"] / 100))

    observaciones = []
    if secciones == "6":
        observaciones.append(
            "Tu proyecto requiere 6 o más secciones: el precio cubre las 5 secciones del "
            "paquete Profesional y las secciones adicionales se cotizarán a la medida."
        )
    tope = cat.PRESUPUESTO_TOPE.get(datos.get("presupuesto"))
    if tope and total > tope:
        observaciones.append(
            "La propuesta rebasa el presupuesto que indicaste. Podemos dividir el "
            "proyecto en fases para que empieces con lo más importante."
        )
    if datos.get("usa_crm") == "pagado":
        observaciones.append(
            "Ya usas un CRM de pago: evaluaremos integrarlo en lugar de reemplazarlo."
        )

    giro = datos.get("giro", "otro")
    return {
        "paquete": paquete,
        "paquete_nombre": cat.PAQUETES[paquete]["nombre"],
        "incluye": list(cat.PAQUETES[paquete]["incluye"]),
        "semanas": cat.PAQUETES[paquete]["semanas"],
        "modulos_giro": list(cat.MODULOS_GIRO.get(giro, cat.MODULOS_GIRO["otro"])),
        "puntaje": puntos,
        "umbral": umbral,
        "desglose": desglose,
        "precio": precio,
        "iva_pct": int(p["iva_pct"]),
        "iva": iva,
        "total": total,
        "anticipo_pct": int(p["anticipo_pct"]),
        "anticipo": anticipo,
        "mantenimiento": mant,
        "mantenimiento_con_iva": mant_iva,
        "vigencia_dias": int(p["vigencia_dias"]),
        "observaciones": observaciones,
    }
