from decimal import Decimal, InvalidOperation
from io import BytesIO
from itertools import groupby

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from openpyxl import Workbook

from inventario.carga import ErrorCarga, carga_siguiente, importar_excel, recalcular_variacion
from inventario.models import CargaInventario, ItemInventario, PrecioReferencia, margen_actual
from inventario.referencias import listar_referencias, precios_de, promedio
from inventario.templatetags.inventario_extras import en_miles, peso
from inventario.seleccion import etiqueta_bodega, orden_bodega


def lista(request):
    cargas = CargaInventario.objects.all()
    if request.GET.get("carga"):
        carga = get_object_or_404(CargaInventario, pk=request.GET.get("carga"))
    else:
        carga = cargas.first()

    filtros = _filtros(request)
    margen = margen_actual()
    referencias = []
    opciones = {}
    if carga:
        opciones = _opciones(carga)
        referencias = listar_referencias(carga, filtros, margen)

    paginador = Paginator(referencias, 30)
    pagina = paginador.get_page(request.GET.get("page"))
    parametros = request.GET.copy()
    parametros.pop("page", None)

    return render(
        request,
        "inventario/lista.html",
        {
            "cargas": cargas,
            "carga": carga,
            "pagina": pagina,
            "filtros": filtros,
            "opciones": opciones,
            "consulta": parametros.urlencode(),
            "hay_filtros": any(filtros.values()),
            "variaciones": ItemInventario.Variacion.choices,
            "margen": margen,
        },
    )


def descargar(request):
    if request.GET.get("carga"):
        carga = get_object_or_404(CargaInventario, pk=request.GET.get("carga"))
    else:
        carga = CargaInventario.objects.first()
    if carga is None:
        raise Http404("No hay inventario para descargar.")

    referencias = listar_referencias(carga, _filtros(request), margen_actual())
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Inventario"
    hoja.append(
        [
            "Código",
            "Nombre",
            "Clase",
            "Color",
            "Red",
            "SIM",
            "RAM",
            "Almacenamiento",
            "Bodegas",
            "Existencia",
            "Costo",
            "Difusión",
            "Renta",
            "Margen %",
            "Precio mínimo",
            "Precio máximo",
            "Promediado",
            "Variación",
        ]
    )
    for fila in referencias:
        hoja.append(
            [
                fila.codigo,
                fila.nombre,
                fila.clase,
                fila.color,
                fila.red,
                fila.tipo_sim,
                fila.ram,
                fila.almacenamiento,
                ", ".join(
                    f"{sede['etiqueta']} ({_entero(sede['existencia'])})" for sede in fila.bodegas
                ),
                float(fila.existencia),
                float(fila.costo),
                float(fila.difusion),
                float(fila.renta),
                float(fila.margen_porcentaje),
                float(fila.precio_minimo),
                float(fila.precio_maximo),
                "Sí" if fila.promediado else "No",
                fila.get_variacion_display(),
            ]
        )

    buffer = BytesIO()
    libro.save(buffer)
    respuesta = HttpResponse(
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    respuesta["Content-Disposition"] = 'attachment; filename="inventario-ygstock.xlsx"'
    return respuesta


def cargar(request):
    if request.method == "POST":
        archivo = request.FILES.get("archivo")
        if not archivo:
            messages.error(request, "Selecciona el Excel descargado de YG.")
            return redirect("inventario:cargar")
        try:
            carga = importar_excel(archivo)
        except ErrorCarga as exc:
            messages.error(request, str(exc))
            return redirect("inventario:cargar")
        messages.success(request, _mensaje_carga(carga))
        return redirect(f"/?carga={carga.pk}")
    return render(request, "inventario/cargar.html")


def cargas(request):
    return render(request, "inventario/cargas.html", {"cargas": CargaInventario.objects.all()})


@require_POST
def eliminar_carga(request, pk):
    carga = get_object_or_404(CargaInventario, pk=pk)
    siguiente = carga_siguiente(carga)
    archivo = carga.archivo
    carga.delete()
    if siguiente:
        recalcular_variacion(siguiente)
    messages.success(request, f"Se eliminó la carga {archivo}.")
    return redirect("inventario:cargas")


@require_POST
def guardar_margenes(request):
    margen = margen_actual()
    destino = _destino(request.POST.get("siguiente"))
    try:
        minimo = Decimal((request.POST.get("minimo") or "2").replace(",", "."))
        maximo = Decimal((request.POST.get("maximo") or "4").replace(",", "."))
    except InvalidOperation:
        messages.error(request, "Los porcentajes deben ser números.")
        return redirect(destino)
    if minimo < 0 or maximo < 0 or maximo < minimo:
        messages.error(request, "El máximo tiene que ser igual o mayor que el mínimo.")
        return redirect(destino)
    margen.porcentaje_minimo = minimo.quantize(Decimal("0.01"))
    margen.porcentaje_maximo = maximo.quantize(Decimal("0.01"))
    margen.save()
    messages.success(
        request,
        f"Rango sobre el costo: mínimo {margen.porcentaje_minimo}% y máximo {margen.porcentaje_maximo}%.",
    )
    return redirect(destino)


@require_POST
def guardar_precio(request):
    codigo = (request.POST.get("codigo") or "").strip()
    campo = request.POST.get("campo") or ""
    if campo not in {"difusion", "renta", "margen"}:
        return JsonResponse({"error": "Ese dato no se puede editar."}, status=400)

    if request.POST.get("carga"):
        carga = get_object_or_404(CargaInventario, pk=request.POST.get("carga"))
    else:
        carga = CargaInventario.objects.first()
    if carga is None:
        return JsonResponse({"error": "No hay inventario cargado."}, status=404)

    items = list(carga.items.filter(codigo=codigo))
    if not items:
        return JsonResponse({"error": "Ese código no está en este corte."}, status=404)
    costo = promedio(item.costo for item in items)
    if costo <= 0:
        return JsonResponse({"error": "El costo de este producto es cero."}, status=400)

    try:
        valor = Decimal((request.POST.get("valor") or "").replace(",", ".").replace("%", ""))
    except InvalidOperation:
        return JsonResponse({"error": "Escribe un número."}, status=400)

    rango = margen_actual()
    ajuste, _ = PrecioReferencia.objects.get_or_create(codigo=codigo)
    operativo = ajuste.margen if ajuste.margen is not None else rango.porcentaje_minimo

    if campo == "margen":
        operativo = valor
    elif campo == "difusion":
        base = (valor * Decimal(1000) / Decimal("1.01")).quantize(Decimal("0.01"))
        operativo = (base / costo - 1) * Decimal(100)
    else:
        operativo = valor * Decimal(1000) / costo * Decimal(100)

    operativo = operativo.quantize(Decimal("0.01"))
    if operativo < 0 or operativo > 1000:
        return JsonResponse({"error": "El porcentaje tiene que estar entre 0 y 1000."}, status=400)

    ajuste.margen = operativo
    ajuste.save()
    return _respuesta_precios(costo, operativo, rango.porcentaje_minimo, rango.porcentaje_maximo)


def historial(request, codigo):
    items = list(
        ItemInventario.objects.filter(codigo=codigo)
        .select_related("carga")
        .order_by("carga__fecha_corte", "carga_id", "bodega")
    )
    if not items:
        raise Http404("No hay historial para este código.")

    margen = margen_actual()
    grupos = []
    for _, filas in groupby(items, key=lambda item: item.carga_id):
        grupos.append(listar_referencias_de(list(filas), margen))
    maximo = max((grupo.costo for grupo in grupos), default=Decimal("1")) or Decimal("1")
    for grupo in grupos:
        grupo.altura = max(4, int((grupo.costo / maximo) * 100))

    return render(
        request,
        "inventario/historial.html",
        {
            "producto": grupos[-1],
            "grupos": grupos,
            "codigo": codigo,
        },
    )


def listar_referencias_de(filas, margen):
    from inventario.referencias import Referencia

    ajuste = PrecioReferencia.objects.filter(codigo=filas[0].codigo).first()
    return Referencia(filas, margen, ajuste)


def _filtros(request):
    return {
        "q": (request.GET.get("q") or "").strip(),
        "bodega": request.GET.get("bodega") or "",
        "clase": request.GET.get("clase") or "",
        "color": request.GET.get("color") or "",
        "red": request.GET.get("red") or "",
        "tipo_sim": request.GET.get("tipo_sim") or "",
        "variacion": request.GET.get("variacion") or "",
    }


def _opciones(carga):
    base = carga.items.all()
    bodegas = sorted(set(base.exclude(bodega="").values_list("bodega", flat=True)), key=orden_bodega)
    return {
        "bodegas": [{"valor": nombre, "etiqueta": etiqueta_bodega(nombre)} for nombre in bodegas],
        "clases": _valores(base, "clase"),
        "colores": _valores(base, "color"),
        "redes": _valores(base, "red"),
        "sims": _valores(base, "tipo_sim"),
    }


def _valores(items, campo):
    return list(items.exclude(**{campo: ""}).values_list(campo, flat=True).distinct().order_by(campo))


def _destino(valor):
    destino = valor or "/"
    if not destino.startswith("/") or destino.startswith("//"):
        return "/"
    return destino


def _respuesta_precios(costo, margen_operativo, porcentaje_minimo, porcentaje_maximo):
    datos = precios_de(costo, margen_operativo, porcentaje_minimo, porcentaje_maximo)
    return JsonResponse(
        {
            "texto": {
                "difusion": peso(datos["difusion"]),
                "minimo": peso(datos["minimo"]),
                "maximo": peso(datos["maximo"]),
                "renta": peso(datos["renta"]),
                "margen": f"{datos['margen']}%",
            },
            "valor": {
                "difusion": en_miles(datos["difusion"]),
                "minimo": en_miles(datos["minimo"]),
                "maximo": en_miles(datos["maximo"]),
                "renta": en_miles(datos["renta"]),
                "margen": f"{datos['margen']:.2f}",
            },
        }
    )


def _entero(valor):
    numero = Decimal(valor)
    if numero == numero.to_integral():
        return str(int(numero))
    return str(numero)


def _mensaje_carga(carga):
    texto = (
        f"Se cargaron {carga.filas} ubicaciones de {carga.productos} celulares "
        f"en Monterrey, Almacenamiento y Centro. "
        f"{carga.subieron} subieron de precio, {carga.bajaron} bajaron, "
        f"{carga.iguales} siguieron igual y {carga.sin_historial} no tenían historial."
    )
    descartadas = getattr(carga, "descartadas", 0)
    if descartadas:
        texto += f" Se dejaron fuera {descartadas} filas de otras familias o bodegas."
    if carga.omitidas:
        texto += f" Se omitieron {carga.omitidas} filas sin código o sin costo."
    return texto
