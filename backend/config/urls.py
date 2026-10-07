
from django.contrib import admin
from django.contrib.auth.views import LoginView
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from core import operaciones
from core import views


urlpatterns = [
    path(
        "sw.js",
        views.service_worker,
        name="service_worker",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),

    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html"
        ),
        name="login",
    ),

    path(
        "operaciones/",
        operaciones.panel_operaciones,
        name="panel_operaciones",
    ),

    path(
        "operaciones/capturas/<str:tracking_id>/",
        operaciones.galeria_capturas,
        name="galeria_capturas",
    ),
    path(
        "operaciones/cambiar-estado/",
        operaciones.cambiar_estado_operacion,
        name="cambiar_estado_operacion",
    ),
    path(
        "operaciones/clientes/",
        operaciones.lista_clientes,
        name="lista_clientes",
    ),

    path(
        "operaciones/clientes/<int:customer_number>/",
        operaciones.detalle_cliente,
        name="detalle_cliente",
    ),
    path(
    "operaciones/ordenes/<str:tracking_id>/",
    operaciones.detalle_orden,
    name="detalle_orden",
    ),
    path(
    "operaciones/configuracion/",
    operaciones.configuracion_operaciones,
    name="configuracion_operaciones",
    ),
    path(
        "operaciones/correos/",
        operaciones.lista_correos,
        name="lista_correos",
    ),
    path(
        "operaciones/correos/reintentar/",
        operaciones.reintentar_correo_panel,
        name="reintentar_correo",
    ),
    path(
        "operaciones/correos/descartar/",
        operaciones.descartar_correo_panel,
        name="descartar_correo",
    ),
    path(
        "operaciones/notificar-cliente/",
        operaciones.notificar_cliente_estado,
        name="notificar_cliente_estado",
    ),
    path(
        "operaciones/correo-prueba/",
        operaciones.enviar_correo_prueba,
        name="enviar_correo_prueba",
    ),
    path(
        "operaciones/plantillas-correo/",
        operaciones.plantillas_correo,
        name="plantillas_correo",
    ),
    
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )

