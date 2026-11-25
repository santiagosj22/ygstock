from decimal import Decimal, ROUND_CEILING

from django import template

register = template.Library()

PUNTOS = {
    "Negro": "#1c1917",
    "Blanco": "#f4f4f1",
    "Azul": "#2563eb",
    "Azul claro": "#7dd3fc",
    "Azul oscuro": "#1e3a8a",
    "Azul titanio": "#5b6e82",
    "Azul plata": "#8aa0b4",
    "Rojo": "#dc2626",
    "Rosa": "#e38cb0",
    "Verde": "#16a34a",
    "Morado": "#7c3aed",
    "Lila": "#c4b5fd",
    "Gris": "#6b7280",
    "Plata": "#c0c6ce",
    "Dorado": "#d6b15a",
    "Naranja": "#f97316",
    "Amarillo": "#eab308",
    "Transparente": "#d6d3d1",
    "Natural": "#d6c3a3",
    "Natural titanio": "#c2b6a6",
    "Negro titanio": "#3f3a36",
    "Blanco titanio": "#e7e2da",
    "Bronce": "#b0835a",
    "Vinotinto": "#7f1d1d",
    "Grafito": "#4b5563",
    "Beige": "#e7d7c1",
    "Tornasol": "#7c8ea6",
    "Desert titanio": "#c4b49a",
    "Morado claro": "#c4b5fd",
    "Neon": "#c6f54a",
    "Fucsia": "#d946ef",
    "Cafe": "#8a5a3b",
    "Coral": "#f27d72",
}


@register.filter
def en_miles(valor):
    if valor is None or valor == "":
        return ""
    numero = Decimal(str(valor))
    miles = (abs(numero) / Decimal(1000)).to_integral_value(rounding=ROUND_CEILING)
    signo = "-" if numero < 0 else ""
    return f"{signo}{int(miles)}"


@register.filter
def miles(valor):
    return en_miles(valor)


@register.filter
def peso(valor):
    if valor is None or valor == "":
        return "—"
    numero = Decimal(str(valor))
    signo = "−" if numero < 0 else ""
    miles = (abs(numero) / Decimal(1000)).to_integral_value(rounding=ROUND_CEILING)
    texto = f"{int(miles):,}".replace(",", ".")
    return f"{signo}$ {texto}"


@register.filter
def delta(valor):
    if valor is None or valor == "":
        return ""
    numero = Decimal(str(valor))
    if numero > 0:
        signo = "+"
    elif numero < 0:
        signo = "−"
    else:
        signo = ""
    return f"{signo}{peso(abs(numero))}"


@register.filter
def cantidad(valor):
    if valor is None or valor == "":
        return "0"
    numero = Decimal(str(valor))
    if numero == numero.to_integral():
        return f"{int(numero):,}".replace(",", ".")
    return f"{numero.normalize():f}".replace(".", ",")


@register.filter
def punto_color(nombre):
    if not nombre:
        return ""
    clave = str(nombre).casefold()
    for texto, color in PUNTOS.items():
        if texto.casefold() == clave:
            return color
    tono = sum(ord(caracter) for caracter in clave) % 360
    return f"hsl({tono} 52% 46%)"
