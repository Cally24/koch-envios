from django.urls import path

from . import views


urlpatterns = [
    # ========================================================
    # CLIENTES
    # ========================================================

    path(
        "clientes/registrar/",
        views.registrar_cliente,
        name="registrar_cliente",
    ),

    path(
        "clientes/buscar/",
        views.buscar_cliente,
        name="buscar_cliente",
    ),

    # ========================================================
    # ÓRDENES
    # ========================================================

    path(
        "ordenes/crear_orden/",
        views.crear_orden,
        name="crear_orden",
    ),

    path(
        "ordenes/cambiar_estado/",
        views.cambiar_estado_orden,
        name="cambiar_estado_orden",
    ),

    # ========================================================
    # TRACKING
    # ========================================================

    path(
        "tracking/buscar/",
        views.buscar_tracking,
        name="buscar_tracking",
    ),

    # ========================================================
    # CONFIGURACION
    # ========================================================

    path(
        "configuracion/",
        views.obtener_configuracion,
        name="obtener_configuracion",
    ),
    # ========================================================
    # PUSH NOTIFICATIONS
    # ========================================================

    path(
        "push/suscripcion/",
        views.guardar_suscripcion_push,
        name="guardar_suscripcion_push",
    ),
]