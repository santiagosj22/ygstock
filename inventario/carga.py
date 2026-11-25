"""Lee el Excel de YG tal como se descarga y acumula el corte."""

import re
import unicodedata
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from zipfile import BadZipFile

import openpyxl
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from openpyxl.utils.exceptions import InvalidFileException

from inventario.models import CargaInventario, ItemInventario
from inventario.parser import parse_descripcion
from inventario.referencias import promedio
from inventario.seleccion import bodega_permitida, familia_permitida

COLUMNAS = ("codigo", "nombre", "descripcion", "familia", "bodega", "costo", "existencia")
ETIQUETAS = {
    "codigo": "Código",
    "nombre": "Nombre",
    "descripcion": "Descripcion",
    "familia": "Familia",
    "bodega": "Bodega",
    "costo": "Costo",
    "existencia": "Existencia",
}


class ErrorCarga(Exception):
    pass


def importar_excel(archivo):
    nombre = (getattr(archivo, "name", "") or "inventario.xlsx").strip()
    if not nombre.lower().endswith(".xlsx"):
        raise ErrorCarga("El archivo debe ser un Excel .xlsx, tal como lo descarga YG.")

    contenido = archivo.read()
    if not contenido:
        raise ErrorCarga("El archivo está vacío.")

    try:
        libro = openpyxl.load_workbook(BytesIO(contenido), data_only=True, read_only=True)
    except (InvalidFileException, BadZipFile, OSError, ValueError) as exc:
        raise ErrorCarga("No se pudo leer el Excel. Súbelo tal como se descarga, sin convertirlo.") from exc

    try:
        filas, fecha, omitidas, descartadas = _leer_libro(libro)
    finally:
        libro.close()

    if not filas:
        if descartadas:
            raise ErrorCarga(
                "El Excel no tiene celulares en Monterrey, Almacenamiento o Centro."
            )
        raise ErrorCarga("El Excel no tiene productos con código y costo.")

    if fecha is None:
        fecha = _fecha_desde_nombre(nombre) or timezone.now()
    fecha = _en_zona(fecha)

    with transaction.atomic():
        carga = CargaInventario.objects.create(
            archivo=nombre[:255],
            fecha_corte=fecha,
            omitidas=omitidas,
        )
        items = []
        for fila in filas:
            items.append(
                ItemInventario(
                    carga=carga,
                    **fila,
                    **parse_descripcion(fila["descripcion"]),
                )
            )
        _asignar_variacion(carga, items)
        ItemInventario.objects.bulk_create(items, batch_size=500)
        _guardar_contadores(carga, items)
        siguiente = carga_siguiente(carga)
        if siguiente:
            recalcular_variacion(siguiente)
    carga.descartadas = descartadas
    return carga


def recalcular_variacion(carga):
    items = list(carga.items.all())
    _asignar_variacion(carga, items)
    if items:
        ItemInventario.objects.bulk_update(
            items,
            ["costo_anterior", "diferencia", "variacion"],
            batch_size=500,
        )
    _guardar_contadores(carga, items)


def carga_siguiente(carga):
    return (
        CargaInventario.objects.exclude(pk=carga.pk)
        .filter(
            Q(fecha_corte__gt=carga.fecha_corte)
            | Q(fecha_corte=carga.fecha_corte, pk__gt=carga.pk)
        )
        .order_by("fecha_corte", "pk")
        .first()
    )


def _leer_libro(libro):
    for hoja in libro.worksheets:
        filas = list(hoja.iter_rows(values_only=True))
        resultado = _interpretar(filas)
        if resultado is not None:
            return resultado
    raise ErrorCarga(
        "No encontré los encabezados Código, Nombre, Descripcion, Familia, Bodega, Costo y Existencia."
    )


def _interpretar(filas):
    encabezado = None
    indice_encabezado = None
    for indice, fila in enumerate(filas[:40]):
        if not fila:
            continue
        nombres = [_norm_encabezado(celda) for celda in fila]
        if "codigo" in nombres:
            encabezado = nombres
            indice_encabezado = indice
            break
    if encabezado is None:
        return None

    indices = {}
    for columna in COLUMNAS:
        try:
            indices[columna] = encabezado.index(columna)
        except ValueError:
            indices[columna] = None
    faltan = [ETIQUETAS[columna] for columna in COLUMNAS if indices[columna] is None]
    if faltan:
        raise ErrorCarga("Faltan columnas: " + ", ".join(faltan) + ".")

    indice_fecha = None
    if "fecha exportacion" in encabezado:
        indice_fecha = encabezado.index("fecha exportacion")

    unicos = {}
    orden = []
    omitidas = 0
    descartadas = 0
    fecha = None
    for fila in filas[indice_encabezado + 1 :]:
        if not fila or not any(celda not in (None, "") for celda in fila):
            continue
        if fecha is None and indice_fecha is not None:
            fecha = _parse_fecha(_celda(fila, indice_fecha))
        codigo = _texto(_celda(fila, indices["codigo"]))[:64]
        if not codigo:
            omitidas += 1
            continue
        costo = _a_decimal(_celda(fila, indices["costo"]))
        if costo is None:
            omitidas += 1
            continue
        existencia = _a_decimal(_celda(fila, indices["existencia"]))
        if existencia is None:
            existencia = Decimal("0")
        descripcion = _texto(_celda(fila, indices["descripcion"]))
        nombre = _texto(_celda(fila, indices["nombre"])) or descripcion or codigo
        datos = {
            "codigo": codigo,
            "nombre": nombre[:500],
            "descripcion": descripcion,
            "familia": _texto(_celda(fila, indices["familia"]))[:120],
            "bodega": _texto(_celda(fila, indices["bodega"]))[:120],
            "costo": costo.quantize(Decimal("0.01")),
            "existencia": existencia.quantize(Decimal("0.01")),
        }
        if not familia_permitida(datos["familia"]) or not bodega_permitida(datos["bodega"]):
            descartadas += 1
            continue
        llave = (datos["codigo"], datos["bodega"])
        if llave not in unicos:
            orden.append(llave)
        unicos[llave] = datos

    return [unicos[llave] for llave in orden], fecha, omitidas, descartadas


def _asignar_variacion(carga, items):
    previos = _costos_previos(carga)
    por_codigo = {}
    for item in items:
        por_codigo.setdefault(item.codigo, []).append(item.costo)
    promedios = {codigo: promedio(costos) for codigo, costos in por_codigo.items()}
    for item in items:
        anterior = previos.get(item.codigo)
        item.costo_anterior, item.diferencia, item.variacion = _clasificar(promedios[item.codigo], anterior)


def _costos_previos(carga):
    anteriores = (
        ItemInventario.objects.exclude(carga=carga)
        .filter(
            Q(carga__fecha_corte__lt=carga.fecha_corte)
            | Q(carga__fecha_corte=carga.fecha_corte, carga__pk__lt=carga.pk)
        )
        .order_by("carga__fecha_corte", "carga_id")
    )
    carga_de = {}
    costos = {}
    for item in anteriores:
        if carga_de.get(item.codigo) != item.carga_id:
            carga_de[item.codigo] = item.carga_id
            costos[item.codigo] = []
        costos[item.codigo].append(item.costo)
    return {codigo: promedio(valores) for codigo, valores in costos.items()}


def depurar_cargas():
    """Deja solo celulares de Monterrey, Almacenamiento y Centro."""
    cargas = CargaInventario.objects.order_by("fecha_corte", "pk")
    for carga in cargas:
        sobran = [
            item.pk
            for item in carga.items.all()
            if not familia_permitida(item.familia) or not bodega_permitida(item.bodega)
        ]
        if sobran:
            ItemInventario.objects.filter(pk__in=sobran).delete()
        recalcular_variacion(carga)


def _clasificar(costo, anterior):
    if anterior is None:
        return None, None, ItemInventario.Variacion.SIN_HISTORIAL
    diferencia = (costo - anterior).quantize(Decimal("0.01"))
    if diferencia > 0:
        variacion = ItemInventario.Variacion.SUBIO
    elif diferencia < 0:
        variacion = ItemInventario.Variacion.BAJO
    else:
        variacion = ItemInventario.Variacion.IGUAL
    return anterior, diferencia, variacion


def _guardar_contadores(carga, items):
    por_codigo = {}
    for item in items:
        por_codigo[item.codigo] = item.variacion
    carga.filas = len(items)
    carga.productos = len(por_codigo)
    carga.subieron = sum(1 for valor in por_codigo.values() if valor == ItemInventario.Variacion.SUBIO)
    carga.bajaron = sum(1 for valor in por_codigo.values() if valor == ItemInventario.Variacion.BAJO)
    carga.iguales = sum(1 for valor in por_codigo.values() if valor == ItemInventario.Variacion.IGUAL)
    carga.sin_historial = sum(
        1 for valor in por_codigo.values() if valor == ItemInventario.Variacion.SIN_HISTORIAL
    )
    carga.save(
        update_fields=["filas", "productos", "subieron", "bajaron", "iguales", "sin_historial"]
    )


def _norm_encabezado(valor):
    texto = unicodedata_norm(str(valor or "")).lower()
    return re.sub(r"\s+", " ", texto).strip()


def unicodedata_norm(texto):
    normalizado = unicodedata.normalize("NFKD", texto)
    return "".join(caracter for caracter in normalizado if not unicodedata.combining(caracter))


def _celda(fila, indice):
    if indice is None or indice >= len(fila):
        return None
    return fila[indice]


def _texto(valor):
    if valor is None:
        return ""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, int) and not isinstance(valor, bool):
        return str(valor)
    return str(valor).strip()


def _a_decimal(valor):
    if valor is None or valor == "" or isinstance(valor, bool):
        return None
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    texto = str(valor).strip().replace("$", "").replace(" ", "")
    if not texto or texto.upper() == "N/A":
        return None
    if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", texto):
        texto = texto.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", texto):
        texto = texto.replace(",", "")
    elif "," in texto and "." not in texto:
        if re.fullmatch(r"\d+,\d{1,2}", texto):
            texto = texto.replace(",", ".")
        else:
            texto = texto.replace(",", "")
    try:
        return Decimal(texto)
    except InvalidOperation:
        return None


def _parse_fecha(valor):
    if isinstance(valor, datetime):
        return valor
    texto = re.sub(r"\s+", " ", str(valor or "").strip())
    if not texto or texto.upper() == "N/A":
        return None
    coincidencia = re.fullmatch(
        r"(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2})(?::(\d{2}))?(?:\s*([AaPp][Mm]))?",
        texto,
    )
    if not coincidencia:
        return None
    anio, mes, dia, hora, minuto, segundo, ampm = coincidencia.groups()
    hora = int(hora)
    if ampm:
        if ampm.lower() == "pm" and hora != 12:
            hora += 12
        if ampm.lower() == "am" and hora == 12:
            hora = 0
    try:
        return datetime(int(anio), int(mes), int(dia), hora, int(minuto), int(segundo or 0))
    except ValueError:
        return None


def _fecha_desde_nombre(nombre):
    coincidencia = re.search(
        r"(20\d{2})-(\d{2})-(\d{2})[ T_](\d{2})[_:](\d{2})[_:](\d{2})",
        nombre or "",
    )
    if not coincidencia:
        return None
    try:
        return datetime(*(int(parte) for parte in coincidencia.groups()))
    except ValueError:
        return None


def _en_zona(momento):
    if timezone.is_aware(momento):
        return momento
    return timezone.make_aware(momento, timezone.get_current_timezone())
