"""Una fila por código: precio promedio y existencia sumada."""

from decimal import Decimal

from inventario.models import ItemInventario, PrecioReferencia
from inventario.seleccion import etiqueta_bodega, orden_bodega


class Referencia:
    def __init__(self, items, margen, ajuste=None):
        items = sorted(items, key=lambda item: (orden_bodega(item.bodega), item.bodega))
        base = items[0]
        self.carga = base.carga
        self.codigo = base.codigo
        self.nombre = base.nombre
        self.descripcion = base.descripcion
        self.familia = base.familia
        self.clase = _primero(items, "clase")
        self.color = _primero(items, "color")
        self.red = _primero(items, "red")
        self.tipo_sim = _primero(items, "tipo_sim")
        self.ram = _primero(items, "ram")
        self.almacenamiento = _primero(items, "almacenamiento")
        costos = [item.costo for item in items]
        self.costo = promedio(costos)
        self.promediado = len(set(costos)) > 1
        self.existencia = sum((item.existencia for item in items), Decimal("0"))
        self.costo_anterior = base.costo_anterior
        self.diferencia = base.diferencia
        self.variacion = base.variacion
        self.bodegas = [
            {
                "etiqueta": etiqueta_bodega(item.bodega),
                "existencia": item.existencia,
                "costo": item.costo,
            }
            for item in items
        ]
        operativo = (
            ajuste.margen if ajuste and ajuste.margen is not None else margen.porcentaje_minimo
        )
        precios = precios_de(
            self.costo,
            operativo,
            margen.porcentaje_minimo,
            margen.porcentaje_maximo,
        )
        self.margen_porcentaje = precios["margen"]
        self.precio_minimo = precios["minimo"]
        self.precio_maximo = precios["maximo"]
        self.renta = precios["renta"]
        self.difusion = precios["difusion"]

    def get_variacion_display(self):
        return dict(ItemInventario.Variacion.choices).get(self.variacion, self.variacion)

    @property
    def variacion_label(self):
        return self.get_variacion_display()

    @property
    def porcentaje(self):
        if not self.costo_anterior or self.diferencia is None:
            return None
        return (self.diferencia / self.costo_anterior) * Decimal(100)


def listar_referencias(carga, filtros, margen):
    por_codigo = {}
    for item in carga.items.all():
        por_codigo.setdefault(item.codigo, []).append(item)

    codigos = set(por_codigo)
    consulta = (filtros.get("q") or "").strip().casefold()
    if consulta:
        codigos = {
            codigo
            for codigo, filas in por_codigo.items()
            if codigo in codigos and _coincide(filas, consulta)
        }
    if filtros.get("bodega"):
        codigos = {
            codigo
            for codigo in codigos
            if any(fila.bodega == filtros["bodega"] for fila in por_codigo[codigo])
        }
    for campo in ("clase", "color", "red", "tipo_sim", "ram", "almacenamiento"):
        valor = filtros.get(campo) or ""
        if valor:
            codigos = {
                codigo
                for codigo in codigos
                if any(getattr(fila, campo) == valor for fila in por_codigo[codigo])
            }

    ajustes = {
        fila.codigo: fila
        for fila in PrecioReferencia.objects.filter(codigo__in=codigos)
    }
    referencias = [
        Referencia(por_codigo[codigo], margen, ajustes.get(codigo)) for codigo in codigos
    ]
    variacion = filtros.get("variacion") or ""
    if variacion:
        referencias = [fila for fila in referencias if fila.variacion == variacion]
    if variacion == ItemInventario.Variacion.SUBIO:
        referencias.sort(key=lambda fila: fila.diferencia or Decimal("0"), reverse=True)
    elif variacion == ItemInventario.Variacion.BAJO:
        referencias.sort(key=lambda fila: fila.diferencia or Decimal("0"))
    else:
        referencias.sort(key=lambda fila: (fila.nombre, fila.codigo))
    return referencias


def promedio(costos):
    costos = list(costos)
    if not costos:
        return Decimal("0.00")
    return (sum(costos, Decimal("0")) / Decimal(len(costos))).quantize(Decimal("0.01"))


def aplicar_margen(costo, porcentaje):
    return (costo * (Decimal("1") + Decimal(porcentaje) / Decimal("100"))).quantize(Decimal("0.01"))


def precios_de(costo, margen_operativo, porcentaje_minimo, porcentaje_maximo):
    """Mínimo y máximo son el rango. La renta sale del margen y la difusión es ese precio más 1%."""

    base = aplicar_margen(costo, margen_operativo)
    return {
        "margen": Decimal(margen_operativo).quantize(Decimal("0.01")),
        "minimo": aplicar_margen(costo, porcentaje_minimo),
        "maximo": aplicar_margen(costo, porcentaje_maximo),
        "renta": (base - costo).quantize(Decimal("0.01")),
        "difusion": (base * Decimal("1.01")).quantize(Decimal("0.01")),
    }


def _primero(items, campo):
    for item in items:
        valor = getattr(item, campo)
        if valor:
            return valor
    return ""


def _coincide(filas, consulta):
    for fila in filas:
        texto = " ".join(
            (
                fila.codigo or "",
                fila.nombre or "",
                fila.descripcion or "",
                fila.color or "",
            )
        ).casefold()
        if consulta in texto:
            return True
    return False
