"""Qué filas del Excel de YG entran al inventario."""

import unicodedata

CLAVES_BODEGA = ("MONTERREY", "ALMACENAMIENTO", "CENTRO")


def familia_permitida(familia):
    return _limpio(familia) == "CELULARES"


def bodega_permitida(bodega):
    texto = _limpio(bodega)
    return any(clave in texto for clave in CLAVES_BODEGA)


def etiqueta_bodega(bodega):
    texto = _limpio(bodega)
    if "ALMACENAMIENTO" in texto:
        return "Almacenamiento"
    if "MONTERREY" in texto:
        return "Monterrey"
    if "CENTRO" in texto:
        return "Centro"
    return str(bodega or "").strip() or "Sin bodega"


def orden_bodega(bodega):
    return {"Monterrey": 0, "Almacenamiento": 1, "Centro": 2}.get(etiqueta_bodega(bodega), 9)


def _limpio(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return " ".join(texto.upper().split())
