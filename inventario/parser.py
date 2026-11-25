"""Separa la descripción libre del Excel de YG en campos filtrables."""

import re
import unicodedata

SIM_RE = re.compile(r"\b(?:E\s*-\s*SIM|S\s*-\s*FIS|SIM\s*-\s*FIS|SIM\s*-\s*F)\b", re.IGNORECASE)
RAM_RE = re.compile(r"\b(\d+)\s*\+\s*(\d+)\s*(GB|TB)\b", re.IGNORECASE)
STORAGE_RE = re.compile(r"\b(\d+)\s*(GB|TB)\b", re.IGNORECASE)
RED_RE = re.compile(r"\b([45]G)\b", re.IGNORECASE)

CLASES = (
    (re.compile(r"\bOPEN\s+BOX\b"), "Open box"),
    (re.compile(r"\bEXH\b"), "Exhibición"),
    (re.compile(r"\bUSADO\b"), "Usado"),
    (re.compile(r"\bNUEVO\b"), "Nuevo"),
    (re.compile(r"\bNUEVA\b"), "Nuevo"),
    (re.compile(r"\bOUTLET\b"), "Outlet"),
)

RUIDO = {
    "TOUCHBAR",
    "WIFI",
    "WI-FI",
    "GPS",
    "SPORT",
    "GLB",
    "GBL",
    "SPECS",
    "SPECES",
    "ORIGINAL",
    "HOMOLOGADO",
    "CPO",
    "MM",
    "INCH",
    "NOISE",
    "CANCELLATION",
    "CANCELATION",
    "NOICE",
    "REPLICA",
}

SUSTITUTOS = {
    "TITANIUM": "TITANIO",
    "BLANCA": "BLANCO",
    "PLATEADO": "PLATA",
    "SILVER": "PLATA",
    "GOLD": "DORADO",
    "GRAPHITE": "GRAFITO",
    "NARANJADO": "NARANJA",
    "ROSADO": "ROSA",
}

_COLORES = (
    "NATURAL TITANIUM",
    "NATURAL TITANIO",
    "NEGRO TITANIUM",
    "NEGRO TITANIO",
    "AZUL TITANIUM",
    "AZUL TITANIO",
    "BLANCO TITANIUM",
    "BLANCO TITANIO",
    "AZUL PLATA",
    "AZUL CLARO",
    "AZUL OSCURO",
    "GRIS ESPACIAL",
    "NEGRO ESPACIAL",
    "NEGRO",
    "BLANCO",
    "BLANCA",
    "AZUL",
    "ROJO",
    "ROSA",
    "ROSADO",
    "VERDE",
    "MORADO",
    "LILA",
    "GRIS",
    "PLATA",
    "DORADO",
    "NARANJA",
    "NARANJADO",
    "AMARILLO",
    "TRANSPARENTE",
    "NATURAL",
    "BRONCE",
    "VINOTINTO",
    "PLATEADO",
    "GRAFITO",
    "GRAPHITE",
    "BEIGE",
    "CREMA",
    "CORAL",
    "CELESTE",
    "TURQUESA",
    "FUCSIA",
    "VIOLETA",
    "CAFE",
    "MARRON",
    "ARENA",
    "OLIVO",
    "LAVANDA",
    "TORNASOL",
    "ORO",
    "SILVER",
    "GOLD",
    "STARLIGHT",
    "MIDNIGHT",
    "TITANIUM",
    "TITANIO",
)
COLORES = tuple(sorted(_COLORES, key=len, reverse=True))


def parse_descripcion(descripcion):
    texto = _mayusculas(descripcion)
    if not texto:
        return _vacio()

    clase = _encontrar_clase(texto)
    sim = _ultima(SIM_RE, texto)
    ram = _ultima(RAM_RE, texto)
    almacenamiento = None if ram else _ultima(STORAGE_RE, texto)
    red = _ultima(RED_RE, texto)

    # La SIM a veces va después del color, así que el corte del color
    # empieza en RAM, almacenamiento o red, no en la SIM.
    fin_spec = 0
    for coincidencia in (ram, almacenamiento, red):
        if coincidencia:
            fin_spec = max(fin_spec, coincidencia.end())

    color = _extraer_color(texto, clase, fin_spec, sim)
    ram_texto = ""
    almacenamiento_texto = ""
    if ram:
        ram_texto = f"{int(ram.group(1))} GB"
        almacenamiento_texto = f"{int(ram.group(2))} {ram.group(3).upper()}"
    elif almacenamiento:
        almacenamiento_texto = f"{int(almacenamiento.group(1))} {almacenamiento.group(2).upper()}"

    return {
        "clase": clase[0] if clase else "",
        "color": color,
        "red": red.group(1).upper() if red else "",
        "tipo_sim": _etiqueta_sim(sim),
        "ram": ram_texto,
        "almacenamiento": almacenamiento_texto,
    }


def _vacio():
    return {
        "clase": "",
        "color": "",
        "red": "",
        "tipo_sim": "",
        "ram": "",
        "almacenamiento": "",
    }


def _mayusculas(valor):
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(caracter for caracter in texto if not unicodedata.combining(caracter))
    return re.sub(r"\s+", " ", texto).strip().upper()


def _ultima(patron, texto):
    hallada = None
    for coincidencia in patron.finditer(texto):
        hallada = coincidencia
    return hallada


def _encontrar_clase(texto):
    mejor = None
    for patron, etiqueta in CLASES:
        for coincidencia in patron.finditer(texto):
            if mejor is None or coincidencia.start() > mejor[1]:
                mejor = (etiqueta, coincidencia.start(), coincidencia.end())
    return mejor


def _etiqueta_sim(coincidencia):
    if not coincidencia:
        return ""
    token = re.sub(r"\s+", "", coincidencia.group(0)).upper()
    if token.startswith("E"):
        return "E-SIM"
    return "SIM física"


def _extraer_color(texto, clase, fin_spec, sim):
    if fin_spec:
        cola = texto[fin_spec:]
        tramos = []
        if sim and sim.end() > fin_spec:
            tramos.append((max(0, sim.start() - fin_spec), sim.end() - fin_spec))
        if clase and clase[2] > fin_spec:
            tramos.append((max(0, clase[1] - fin_spec), clase[2] - fin_spec))
        return _normalizar_color(_limpiar_cola(_borrar_tramos(cola, tramos)))
    if clase and texto[clase[2] :].strip():
        return _normalizar_color(_limpiar_cola(texto[clase[2] :]))
    fin = clase[1] if clase else len(texto)
    return _normalizar_color(_color_al_final(texto[:fin]))


def _borrar_tramos(texto, tramos):
    caracteres = list(texto)
    for inicio, fin in tramos:
        for indice in range(max(0, inicio), min(len(caracteres), fin)):
            caracteres[indice] = " "
    return "".join(caracteres)


def _limpiar_cola(cola):
    tokens = []
    for token in cola.replace("-", " ").split():
        token = token.strip("()[]\"'")
        if not token or token in RUIDO:
            continue
        if re.fullmatch(r"\d+", token) or re.fullmatch(r"M\d+", token):
            continue
        if re.fullmatch(r"\d+(DA|RA|TA|MA)", token):
            continue
        tokens.append(token)
    return " ".join(tokens)


def _color_al_final(texto):
    recortado = texto.strip(" -\"'")
    for color in COLORES:
        if recortado == color or recortado.endswith(" " + color):
            return color
    return ""


def _normalizar_color(color):
    if not color:
        return ""
    tokens = [SUSTITUTOS.get(token, token) for token in color.split()]
    return " ".join(token.capitalize() for token in tokens)
