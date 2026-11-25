from decimal import Decimal

from django.db import models


class MargenVenta(models.Model):
    porcentaje_minimo = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("2"))
    porcentaje_maximo = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("4"))

    class Meta:
        verbose_name = "margen de venta"
        verbose_name_plural = "margen de venta"

    def __str__(self):
        return f"{self.porcentaje_minimo}% – {self.porcentaje_maximo}%"


def margen_actual():
    margen, _ = MargenVenta.objects.get_or_create(
        pk=1,
        defaults={
            "porcentaje_minimo": Decimal("2"),
            "porcentaje_maximo": Decimal("4"),
        },
    )
    return margen


class PrecioReferencia(models.Model):
    """Margen definitivo de un código. Vacío significa que sigue el rango global."""

    codigo = models.CharField(max_length=64, unique=True)
    margen = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    porcentaje_maximo = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = "precio de referencia"
        verbose_name_plural = "precios de referencia"

    def __str__(self):
        return self.codigo


class CargaInventario(models.Model):
    archivo = models.CharField(max_length=255)
    fecha_corte = models.DateTimeField()
    creada_en = models.DateTimeField(auto_now_add=True)
    filas = models.PositiveIntegerField(default=0)
    productos = models.PositiveIntegerField(default=0)
    subieron = models.PositiveIntegerField(default=0)
    bajaron = models.PositiveIntegerField(default=0)
    iguales = models.PositiveIntegerField(default=0)
    sin_historial = models.PositiveIntegerField(default=0)
    omitidas = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-fecha_corte", "-id"]
        verbose_name = "carga de inventario"
        verbose_name_plural = "cargas de inventario"

    def __str__(self):
        return f"{self.fecha_corte:%Y-%m-%d %H:%M} · {self.archivo}"


class ItemInventario(models.Model):
    class Variacion(models.TextChoices):
        SUBIO = "subio", "Subió"
        BAJO = "bajo", "Bajó"
        IGUAL = "igual", "Igual"
        SIN_HISTORIAL = "sin_historial", "Primera vez"

    carga = models.ForeignKey(CargaInventario, on_delete=models.CASCADE, related_name="items")
    codigo = models.CharField(max_length=64, db_index=True)
    nombre = models.CharField(max_length=500)
    descripcion = models.TextField(blank=True)
    familia = models.CharField(max_length=120, blank=True, db_index=True)
    bodega = models.CharField(max_length=120, blank=True, db_index=True)
    costo = models.DecimalField(max_digits=14, decimal_places=2)
    existencia = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    clase = models.CharField(max_length=32, blank=True, db_index=True)
    color = models.CharField(max_length=80, blank=True, db_index=True)
    red = models.CharField(max_length=8, blank=True, db_index=True)
    tipo_sim = models.CharField(max_length=32, blank=True, db_index=True)
    ram = models.CharField(max_length=16, blank=True)
    almacenamiento = models.CharField(max_length=16, blank=True, db_index=True)
    costo_anterior = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    diferencia = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    variacion = models.CharField(max_length=20, choices=Variacion.choices, db_index=True)

    class Meta:
        ordering = ["nombre", "bodega", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["carga", "codigo", "bodega"],
                name="item_unico_por_carga",
            )
        ]
        verbose_name = "ítem de inventario"
        verbose_name_plural = "ítems de inventario"

    def __str__(self):
        return f"{self.codigo} · {self.bodega}"

    @property
    def porcentaje(self):
        if not self.costo_anterior or self.diferencia is None:
            return None
        return (self.diferencia / self.costo_anterior) * Decimal(100)
