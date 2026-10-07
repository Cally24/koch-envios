from django.contrib import admin
from django.utils.html import format_html, format_html_join

from .models import (
    Cliente,
    Orden,
    NotaOrden,
    HistorialEstado,
    CapturaOrden,
    Configuracion,
    PlantillaCorreo,
    RegistroCorreo,
)


# ============================================================
# CLIENTES
# ============================================================

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):

    list_display = (
        "customer_number",
        "nombre",
        "apellidos",
        "telefono",
        "email",
        "ciudad",
        "provincia",
        "activo",
        "fecha_registro",
    )

    search_fields = (
        "customer_number",
        "nombre",
        "apellidos",
        "telefono",
        "email",
    )

    list_filter = (
        "activo",
        "provincia",
        "ciudad",
    )

    ordering = (
        "customer_number",
    )

    readonly_fields = (
        "customer_number",
        "fecha_registro",
        "fecha_actualizacion",
    )


# ============================================================
# ÓRDENES
# ============================================================

@admin.register(Orden)
class OrdenAdmin(admin.ModelAdmin):

    list_display = (
        "tracking_id",
        "cliente",
        "tipo",
        "producto",
        "cantidad",
        "peso",
        "precio",
        "estado",
        "fecha_creacion",
    )

    search_fields = (
        "tracking_id",
        "cliente__customer_number",
        "cliente__nombre",
        "cliente__apellidos",
        "producto",
    )

    list_filter = (
        "estado",
        "tipo",
        "fecha_creacion",
    )

    ordering = (
        "-fecha_creacion",
    )

    readonly_fields = (
        "tracking_id",
        "fecha_creacion",
        "fecha_actualizacion",
        "mostrar_capturas",
    )
    def mostrar_capturas(self, obj):
        capturas = obj.capturas.all()

        if not capturas:
            return "Esta orden no tiene capturas."

        return format_html(
            '<div style="display:flex; flex-wrap:wrap; gap:10px;">{}</div>',
            format_html_join(
                "",
                '<div style="display:inline-block; padding:8px; '
                'border:1px solid #ddd; border-radius:8px; background:#fff;">'
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:300px; max-height:300px; '
                'object-fit:contain; display:block;">'
                '</a>'
                '</div>',
                ((captura.archivo.url, captura.archivo.url) for captura in capturas),
            ),
        )

    mostrar_capturas.short_description = "Capturas del pedido"

# ============================================================
# NOTAS DE ÓRDENES
# ============================================================

@admin.register(NotaOrden)
class NotaOrdenAdmin(admin.ModelAdmin):

    list_display = (
        "orden",
        "usuario",
        "fecha",
    )

    search_fields = (
        "orden__tracking_id",
        "usuario",
        "texto",
    )

    list_filter = (
        "fecha",
    )

    ordering = (
        "-fecha",
    )

    readonly_fields = (
        "fecha",
    )


# ============================================================
# HISTORIAL DE ESTADOS
# ============================================================

@admin.register(HistorialEstado)
class HistorialEstadoAdmin(admin.ModelAdmin):

    list_display = (
        "orden",
        "estado_anterior",
        "estado_nuevo",
        "usuario",
        "fecha",
    )

    search_fields = (
        "orden__tracking_id",
        "usuario",
        "nota",
    )

    list_filter = (
        "estado_anterior",
        "estado_nuevo",
        "fecha",
    )

    ordering = (
        "-fecha",
    )

    readonly_fields = (
        "orden",
        "estado_anterior",
        "estado_nuevo",
        "nota",
        "usuario",
        "fecha",
    )

# ============================================================
# CAPTURAS DE ÓRDENES
# ============================================================

@admin.register(CapturaOrden)
class CapturaOrdenAdmin(admin.ModelAdmin):

    list_display = (
        "orden",
        "tracking_id",
        "cliente",
        "fecha",
        "ver_captura",
    )

    search_fields = (
        "orden__tracking_id",
        "orden__cliente__customer_number",
        "orden__cliente__nombre",
        "orden__cliente__apellidos",
    )

    list_filter = (
        "fecha",
    )

    ordering = (
        "-fecha",
    )

    readonly_fields = (
        "orden",
        "fecha",
        "ver_captura",
    )

    def tracking_id(self, obj):
        return obj.orden.tracking_id

    tracking_id.short_description = "Tracking ID"

    def cliente(self, obj):
        return obj.orden.cliente

    cliente.short_description = "Cliente"

    def ver_captura(self, obj):
        if obj.archivo:
            return format_html(
                '<a href="{}" target="_blank">Ver captura</a>',
                obj.archivo.url,
            )

        return "Sin archivo"

    ver_captura.short_description = "Archivo"

# ============================================================
# CONFIGURACIÓN DEL SITIO
# ============================================================

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):

    list_display = (
        "proximo_envio",
        "tarifa_menos_50",
        "tarifa_mas_50",
        "precio_celular",
        "precio_tablet",
        "precio_laptop",
        "fecha_actualizacion",
    )

    readonly_fields = (
        "fecha_actualizacion",
    )

    fieldsets = (
        (
            "Próximo envío",
            {
                "fields": (
                    "proximo_envio",
                ),
            },
        ),
        (
            "Tarifas de envío",
            {
                "fields": (
                    "tarifa_menos_50",
                    "tarifa_mas_50",
                ),
            },
        ),
        (
            "Precios de electrónicos",
            {
                "fields": (
                    "precio_celular",
                    "precio_tablet",
                    "precio_laptop",
                ),
            },
        ),
        (
            "Información",
            {
                "fields": (
                    "fecha_actualizacion",
                ),
            },
        ),
    )


# ============================================================
# PLANTILLAS DE CORREO
# ============================================================

@admin.register(PlantillaCorreo)
class PlantillaCorreoAdmin(admin.ModelAdmin):

    list_display = (
        "evento",
        "asunto",
        "activa",
    )


# ============================================================
# REGISTRO DE CORREOS
# ============================================================

@admin.register(RegistroCorreo)
class RegistroCorreoAdmin(admin.ModelAdmin):

    list_display = (
        "fecha_creacion",
        "evento",
        "destinatario",
        "estado",
        "resuelto",
    )

    list_filter = ("estado", "evento")

    search_fields = ("destinatario", "referencia", "asunto")
