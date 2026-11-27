from datetime import datetime
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from openpyxl import Workbook, load_workbook

from inventario.carga import depurar_cargas, importar_excel
from inventario.models import ItemInventario, PrecioReferencia
from inventario.parser import parse_descripcion
from inventario.templatetags.inventario_extras import peso, punto_color


class ParserTests(TestCase):
    def test_separa_las_descripciones_de_celulares(self):
        casos = [
            (
                "CELULAR APPLE IPHONE 15 PRO MAX 5G 8+256GB E-SIM NATURAL TITANIUM EXH",
                {
                    "clase": "Exhibición",
                    "color": "Natural Titanio",
                    "red": "5G",
                    "tipo_sim": "E-SIM",
                    "ram": "8 GB",
                    "almacenamiento": "256 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 13 PRO 5G 6+1TB E-SIM AZUL EXH",
                {
                    "clase": "Exhibición",
                    "color": "Azul",
                    "red": "5G",
                    "tipo_sim": "E-SIM",
                    "ram": "6 GB",
                    "almacenamiento": "1 TB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS ROSADO EXH",
                {
                    "clase": "Exhibición",
                    "color": "Rosa",
                    "red": "5G",
                    "tipo_sim": "SIM física",
                    "ram": "6 GB",
                    "almacenamiento": "128 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 15 PRO 5G 8+1TB E-SIM NEGRO TITANIO EXH",
                {
                    "clase": "Exhibición",
                    "color": "Negro Titanio",
                    "red": "5G",
                    "tipo_sim": "E-SIM",
                    "ram": "8 GB",
                    "almacenamiento": "1 TB",
                },
            ),
            (
                "CELULAR APPLE IPHONE XR 4G 4+64GB S-FIS NEGRO EXH",
                {
                    "clase": "Exhibición",
                    "color": "Negro",
                    "red": "4G",
                    "tipo_sim": "SIM física",
                    "ram": "4 GB",
                    "almacenamiento": "64 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 11 4G 4+64GB S-FIS BLANCO USADO",
                {
                    "clase": "Usado",
                    "color": "Blanco",
                    "red": "4G",
                    "tipo_sim": "SIM física",
                    "ram": "4 GB",
                    "almacenamiento": "64 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 11 PRO MAX 4G 4+256GB S-FIS VERDE EXH",
                {
                    "clase": "Exhibición",
                    "color": "Verde",
                    "red": "4G",
                    "tipo_sim": "SIM física",
                    "ram": "4 GB",
                    "almacenamiento": "256 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 17 5G 12+256GB E - SIM  LILA NUEVO",
                {
                    "clase": "Nuevo",
                    "color": "Lila",
                    "red": "5G",
                    "tipo_sim": "E-SIM",
                    "ram": "12 GB",
                    "almacenamiento": "256 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 15 PRO 5G 8+128GB S - FIS NEGRO TITANIUM EXH",
                {
                    "clase": "Exhibición",
                    "color": "Negro Titanio",
                    "red": "5G",
                    "tipo_sim": "SIM física",
                    "ram": "8 GB",
                    "almacenamiento": "128 GB",
                },
            ),
            (
                "CELULAR POCO X8 PRO 5G 8+512 GB VERDE NUEVO",
                {
                    "clase": "Nuevo",
                    "color": "Verde",
                    "red": "5G",
                    "tipo_sim": "",
                    "ram": "8 GB",
                    "almacenamiento": "512 GB",
                },
            ),
            (
                "CELULAR SAMSUNG GALAXY A56 5G 8+128GB S-FIS NEGRO OPEN BOX",
                {
                    "clase": "Open box",
                    "color": "Negro",
                    "red": "5G",
                    "tipo_sim": "SIM física",
                    "ram": "8 GB",
                    "almacenamiento": "128 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 17 AIR 5G 12+256GB AZUL E-SIM USADO",
                {
                    "clase": "Usado",
                    "color": "Azul",
                    "red": "5G",
                    "tipo_sim": "E-SIM",
                    "ram": "12 GB",
                    "almacenamiento": "256 GB",
                },
            ),
            (
                "CELULAR APPLE IPHONE 13 4+128GB S-FIS ROJO EXH",
                {
                    "clase": "Exhibición",
                    "color": "Rojo",
                    "red": "",
                    "tipo_sim": "SIM física",
                    "ram": "4 GB",
                    "almacenamiento": "128 GB",
                },
            ),
            (
                "LAPTOP APPLE MACBOOK AIR 2022 M2 13\" 8+256GB USADO DORADO",
                {
                    "clase": "Usado",
                    "color": "Dorado",
                    "red": "",
                    "tipo_sim": "",
                    "ram": "8 GB",
                    "almacenamiento": "256 GB",
                },
            ),
            (
                "VIDRIO CERAMICO GENERICO IPHONE 8 PLASTICO NEGRO",
                {
                    "clase": "",
                    "color": "Negro",
                    "red": "",
                    "tipo_sim": "",
                    "ram": "",
                    "almacenamiento": "",
                },
            ),
            (
                "AUDIFONOS APPLE AIRPODS PRO 2 REPLICA 1.1 NUEVO BLANCO",
                {
                    "clase": "Nuevo",
                    "color": "Blanco",
                    "red": "",
                    "tipo_sim": "",
                    "ram": "",
                    "almacenamiento": "",
                },
            ),
            (
                "FUNDA DE SILICONA PARA IPHONE 17 PRO MAX AZUL CLARO",
                {
                    "clase": "",
                    "color": "Azul Claro",
                    "red": "",
                    "tipo_sim": "",
                    "ram": "",
                    "almacenamiento": "",
                },
            ),
            (
                "BATERIA 16 PRO MAX SIN FLEX NUEVA",
                {
                    "clase": "Nuevo",
                    "color": "",
                    "red": "",
                    "tipo_sim": "",
                    "ram": "",
                    "almacenamiento": "",
                },
            ),
        ]
        for descripcion, esperado in casos:
            with self.subTest(descripcion=descripcion):
                self.assertEqual(parse_descripcion(descripcion), esperado)


class CargaTests(TestCase):
    def test_acumula_cortes_y_marca_si_el_precio_sube_o_baja(self):
        primero = _excel(
            [
                ("0001", "Celular negro", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "4-MONTERREY", 1000, 2),
                ("0001", "Celular negro", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "5-ALMACENAMIENTO", 1000, 4),
                ("0002", "Otro celular", "CELULAR APPLE IPHONE 13 5G 4+128GB E-SIM AZUL EXH", "CELULARES", "2-TIENDA CENTRO", 3500, 10),
                ("0099", "Vidrio", "VIDRIO CERAMICO GENERICO IPHONE 8 PLASTICO BLANCO", "ACCESORIOS", "5-ALMACENAMIENTO", 3500, 10),
                ("0001", "Celular negro", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "8-REPUESTOS", 1000, 1),
            ],
            "2026-11-20 10:00 am",
            "corte-viejo.xlsx",
        )
        carga = importar_excel(primero)
        self.assertEqual(carga.productos, 2)
        self.assertEqual(carga.filas, 3)
        self.assertEqual(carga.sin_historial, 2)
        self.assertEqual(carga.fecha_corte, timezone.make_aware(datetime(2026, 11, 20, 10, 0)))

        item = carga.items.get(codigo="0001", bodega="4-MONTERREY")
        self.assertEqual(item.clase, "Exhibición")
        self.assertEqual(item.color, "Negro")
        self.assertEqual(item.red, "5G")
        self.assertEqual(item.tipo_sim, "SIM física")
        self.assertEqual(item.ram, "6 GB")
        self.assertEqual(item.almacenamiento, "128 GB")
        self.assertEqual(item.existencia, Decimal("2.00"))

        segundo = _excel(
            [
                ("0001", "Celular negro", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "4-MONTERREY", 1200, 1),
                ("0001", "Celular negro", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "5-ALMACENAMIENTO", 1200, 3),
                ("0002", "Otro celular", "CELULAR APPLE IPHONE 13 5G 4+128GB E-SIM AZUL EXH", "CELULARES", "2-TIENDA CENTRO", 3000, 8),
                ("0003", "Cable", "CELULAR APPLE IPHONE 12 4G 4+64GB S-FIS BLANCO NUEVO", "CELULARES", "2-TIENDA CENTRO", 500, 6),
            ],
            "2026-11-24 7:38 pm",
            "INFORME INVENTARIO DE PRODUCTOS 2026-11-24 19_38_13.xlsx",
        )
        reciente = importar_excel(segundo)
        self.assertEqual(reciente.subieron, 1)
        self.assertEqual(reciente.bajaron, 1)
        self.assertEqual(reciente.sin_historial, 1)
        self.assertEqual(reciente.productos, 3)

        subio = reciente.items.filter(codigo="0001").first()
        self.assertEqual(subio.variacion, ItemInventario.Variacion.SUBIO)
        self.assertEqual(subio.diferencia, Decimal("200.00"))
        bajo = reciente.items.get(codigo="0002")
        self.assertEqual(bajo.variacion, ItemInventario.Variacion.BAJO)
        self.assertEqual(bajo.diferencia, Decimal("-500.00"))

    def test_un_corte_viejo_recalcula_el_posterior(self):
        importar_excel(
            _excel(
                [("0001", "A", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL NUEVO", "CELULARES", "2-TIENDA CENTRO", 100, 1)],
                "2026-11-24 10:00 am",
                "nuevo.xlsx",
            )
        )
        importar_excel(
            _excel(
                [("0001", "A", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL NUEVO", "CELULARES", "2-TIENDA CENTRO", 80, 1)],
                "2026-11-20 10:00 am",
                "viejo.xlsx",
            )
        )
        reciente = ItemInventario.objects.get(carga__fecha_corte__day=24)
        anterior = ItemInventario.objects.get(carga__fecha_corte__day=20)
        self.assertEqual(anterior.variacion, ItemInventario.Variacion.SIN_HISTORIAL)
        self.assertEqual(reciente.variacion, ItemInventario.Variacion.SUBIO)
        self.assertEqual(reciente.costo_anterior, Decimal("80.00"))

    def test_la_lista_muestra_tabla_y_tarjetas(self):
        importar_excel(
            _excel(
                [("0001", "iPhone 15", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS ROSADO EXH", "CELULARES", "2-TIENDA CENTRO", 1000, 2)],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "solo-escritorio")
        self.assertContains(respuesta, "solo-movil")
        self.assertContains(respuesta, "iPhone 15")
        self.assertContains(respuesta, 'aria-label="Rosa"')
        self.assertContains(respuesta, 'class="punto"')
        self.assertContains(respuesta, "Primera vez")
        self.assertContains(respuesta, "Difusión")
        self.assertContains(respuesta, 'class="precio-fijo">1<')
        self.assertContains(respuesta, 'class="precio-fijo">2<')
        self.assertNotContains(respuesta, "Costo promedio")
        self.assertContains(respuesta, "Centro")
        self.assertContains(respuesta, 'class="marcar"')
        self.assertContains(respuesta, "WhatsApp")
        self.assertContains(respuesta, "menu-movil")
        self.assertContains(respuesta, 'data-copiar="0001"')
        self.assertContains(respuesta, 'data-ram="6 GB"')
        self.assertContains(respuesta, 'data-clase="Exhibición"')
        self.assertContains(respuesta, "inventario/mensaje.js")
        self.assertContains(respuesta, "Agrupar por referencia")
        self.assertContains(respuesta, "Agrupar por clase")
        self.assertContains(respuesta, "Copiar código")
        self.assertContains(respuesta, 'name="ram"')
        self.assertContains(respuesta, "Memoria")

        historial = self.client.get("/producto/0001/")
        self.assertEqual(historial.status_code, 200)
        self.assertContains(historial, "$ 1")

    def test_promedia_el_costo_y_suma_la_existencia(self):
        importar_excel(
            _excel(
                [
                    ("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "4-MONTERREY", 320, 1),
                    ("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "5-ALMACENAMIENTO", 330, 3),
                ],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.get("/")
        self.assertContains(respuesta, 'class="precio-fijo">1<')
        self.assertContains(respuesta, "Monterrey")
        self.assertContains(respuesta, "Almacenamiento")
        self.assertContains(respuesta, "Costo promedio")
        self.assertContains(respuesta, "Monterrey C1 P")
        self.assertContains(respuesta, "Almacenamiento C3 P")
        self.assertContains(respuesta, 'class="existencia">4<')

    def test_el_excel_descarga_lo_filtrado(self):
        importar_excel(
            _excel(
                [
                    ("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "4-MONTERREY", 320, 1),
                    ("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB S-FIS NEGRO EXH", "CELULARES", "5-ALMACENAMIENTO", 330, 3),
                    ("0002", "Otro", "CELULAR APPLE IPHONE 13 5G 4+128GB E-SIM AZUL EXH", "CELULARES", "2-TIENDA CENTRO", 100, 1),
                ],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.get("/descargar/?clase=Exhibición&color=Negro")
        self.assertEqual(
            respuesta["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        libro = load_workbook(BytesIO(respuesta.content))
        filas = list(libro.active.iter_rows(values_only=True))
        self.assertEqual(filas[1][0], "0001")
        self.assertEqual(filas[1][10], 325)
        self.assertEqual(filas[1][11], 338.13)
        self.assertEqual(filas[1][12], 6.5)
        self.assertEqual(filas[1][13], 2)
        self.assertEqual(filas[1][16], "Sí")
        self.assertEqual(len(filas), 2)

    def test_los_margenes_se_pueden_cambiar(self):
        importar_excel(
            _excel(
                [("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL NUEVO", "CELULARES", "4-MONTERREY", 1000000, 1)],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.post("/margenes/", {"minimo": "10", "maximo": "20", "siguiente": "/"})
        self.assertEqual(respuesta.status_code, 302)
        pagina = self.client.get("/")
        self.assertContains(pagina, 'class="precio-fijo">1100<')
        self.assertContains(pagina, 'class="precio-fijo">1122<')
        self.assertContains(pagina, 'class="precio-fijo">1200<')

    def test_editar_el_margen_recalcula_difusion_y_renta(self):
        importar_excel(
            _excel(
                [("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL NUEVO", "CELULARES", "4-MONTERREY", 1000000, 1)],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.post("/precios/", {"codigo": "0001", "campo": "margen", "valor": "4"})
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertEqual(datos["texto"]["minimo"], "$ 1.020")
        self.assertEqual(datos["texto"]["maximo"], "$ 1.040")
        self.assertEqual(datos["texto"]["difusion"], "$ 1.061")
        self.assertEqual(datos["texto"]["renta"], "$ 40")
        self.assertEqual(datos["texto"]["margen"], "4.00%")
        self.assertEqual(ItemInventario.objects.get(codigo="0001").costo, Decimal("1000000.00"))

        difundido = self.client.post("/precios/", {"codigo": "0001", "campo": "difusion", "valor": "1061"})
        self.assertEqual(difundido.status_code, 200)
        self.assertEqual(difundido.json()["texto"]["margen"], "4.02%")
        self.assertEqual(ItemInventario.objects.get(codigo="0001").costo, Decimal("1000000.00"))

        pagina = self.client.get("/")
        self.assertContains(pagina, "Editar precios")
        self.assertContains(pagina, 'data-campo="renta"')

    def test_el_margen_masivo_solo_toca_la_vista_filtrada(self):
        importar_excel(
            _excel(
                [
                    ("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL EXH", "CELULARES", "4-MONTERREY", 1000000, 1),
                    ("0002", "Otro", "CELULAR APPLE IPHONE 13 5G 4+128GB E-SIM AZUL NUEVO", "CELULARES", "4-MONTERREY", 1000000, 1),
                ],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        respuesta = self.client.post(
            "/margen-vista/",
            {"margen": "8", "siguiente": "/?clase=Exhibición"},
        )
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(PrecioReferencia.objects.get(codigo="0001").margen, Decimal("8.00"))
        self.assertFalse(PrecioReferencia.objects.filter(codigo="0002").exists())
        pagina = self.client.get("/?clase=Exhibición")
        self.assertContains(pagina, "Aplicar a la vista")
        self.assertContains(pagina, 'class="precio-fijo">1102<')
        self.assertContains(pagina, 'class="precio-fijo">1020<')

    def test_depura_familias_y_bodegas_que_no_entran(self):
        carga = importar_excel(
            _excel(
                [("0001", "iPhone", "CELULAR APPLE IPHONE 15 5G 6+128GB E-SIM AZUL NUEVO", "CELULARES", "4-MONTERREY", 1000, 1)],
                "2026-11-24 7:38 pm",
                "informe.xlsx",
            )
        )
        ItemInventario.objects.create(
            carga=carga,
            codigo="0099",
            nombre="Vidrio",
            familia="ACCESORIOS",
            bodega="5-ALMACENAMIENTO",
            costo=Decimal("10.00"),
            existencia=Decimal("1.00"),
            variacion=ItemInventario.Variacion.SIN_HISTORIAL,
        )
        depurar_cargas()
        self.assertFalse(carga.items.filter(codigo="0099").exists())
        self.assertEqual(carga.items.count(), 1)

    def test_el_punto_de_color_no_depende_de_mayusculas(self):
        self.assertEqual(punto_color("Azul Claro"), "#7dd3fc")
        self.assertEqual(punto_color("Negro Titanio"), "#3f3a36")
        self.assertEqual(punto_color("Desert Titanio"), "#c4b49a")
        self.assertTrue(punto_color("Color Raro").startswith("hsl("))

    def test_el_precio_se_muestra_en_miles_redondeado_hacia_arriba(self):
        self.assertEqual(peso(Decimal("1332800")), "$ 1.333")
        self.assertEqual(peso(Decimal("960938")), "$ 961")
        self.assertEqual(peso(Decimal("1332000")), "$ 1.332")
        self.assertEqual(peso(Decimal("2139592.08")), "$ 2.140")


def _excel(filas, fecha, nombre):
    libro = Workbook()
    hoja = libro.active
    hoja.append(["1"])
    hoja.append(["901981867 - 5"])
    hoja.append(["INFORME INVENTARIO DE PRODUCTOS"])
    hoja.append([])
    hoja.append(["Código", "Nombre", "Descripcion", "Familia", "Bodega", "Imp. Venta", "Costo", "Precio V.", "Existencia", "Fecha exportacion"])
    for codigo, nombre_producto, descripcion, familia, bodega, costo, existencia in filas:
        hoja.append([codigo, nombre_producto, descripcion, familia, bodega, None, costo, costo, existencia, fecha])
    buffer = BytesIO()
    libro.save(buffer)
    return SimpleUploadedFile(
        nombre,
        buffer.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
