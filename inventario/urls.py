from django.urls import path

from inventario import views

app_name = "inventario"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("descargar/", views.descargar, name="descargar"),
    path("margenes/", views.guardar_margenes, name="margenes"),
    path("cargar/", views.cargar, name="cargar"),
    path("cargas/", views.cargas, name="cargas"),
    path("cargas/<int:pk>/eliminar/", views.eliminar_carga, name="eliminar_carga"),
    path("producto/<str:codigo>/", views.historial, name="historial"),
]
