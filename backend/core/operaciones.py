import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .models import (
    Orden,
    HistorialEstado,
    Configuracion,
    PlantillaCorreo,
    RegistroCorreo,
)
from .notificaciones import (
    notificar_estado_manual,
    asegurar_plantillas,
    enviar_prueba,
    reintentar_correo,
    VARIABLES_DISPONIBLES,
)


@login_required
def panel_operaciones(request):

    ahora = timezone.localtime()

    inicio_dia = ahora.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    inicio_semana = inicio_dia - timedelta(
        days=ahora.weekday()
    )

    inicio_mes = inicio_dia.replace(
        day=1
    )

    total_ordenes = Orden.objects.count()

    ordenes_hoy = Orden.objects.filter(
        fecha_creacion__gte=inicio_dia
    ).count()

    ordenes_semana = Orden.objects.filter(
        fecha_creacion__gte=inicio_semana
    ).count()

    ordenes_mes = Orden.objects.filter(
        fecha_creacion__gte=inicio_mes
    ).count()

    ordenes = Orden.objects.select_related(
        "cliente"
    ).prefetch_related(
        "capturas"
    ).order_by(
        "-fecha_creacion"
    )

    contexto = {
        "total_ordenes": total_ordenes,
        "ordenes_hoy": ordenes_hoy,
        "ordenes_semana": ordenes_semana,
        "ordenes_mes": ordenes_mes,
        "ordenes": ordenes,
        "correos_fallidos": _contar_correos_fallidos(),
    }

    return render(
        request,
        "operaciones/panel.html",
        contexto
    )


@login_required
def galeria_capturas(request, tracking_id):

    orden = Orden.objects.prefetch_related(
        "capturas"
    ).get(
        tracking_id=tracking_id
    )

    contexto = {
        "orden": orden,
        "capturas": orden.capturas.all(),
    }

    return render(
        request,
        "operaciones/galeria_capturas.html",
        contexto
    )


@login_required
@permission_required(
    "core.can_change_order_status",
    raise_exception=True
)
def cambiar_estado_operacion(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "ok": False,
                "error": "Método no permitido."
            },
            status=405
        )

    tracking_id = request.POST.get(
        "tracking_id",
        ""
    ).strip()

    nuevo_estado = request.POST.get(
        "estado",
        ""
    ).strip()

    estados_validos = {
        "recibida",
        "revision",
        "info_requerida",
        "confirmada",
        "pago_pendiente",
        "pago_recibido",
        "preparando",
        "transito",
        "cuba",
        "disponible",
        "entregada",
        "cancelada",
    }

    if not tracking_id:
        return JsonResponse(
            {
                "ok": False,
                "error": "Falta el tracking ID."
            },
            status=400
        )

    if nuevo_estado not in estados_validos:
        return JsonResponse(
            {
                "ok": False,
                "error": "Estado no válido."
            },
            status=400
        )

    try:
        orden = Orden.objects.get(
            tracking_id=tracking_id
        )
    except Orden.DoesNotExist:
        return JsonResponse(
            {
                "ok": False,
                "error": "Orden no encontrada."
            },
            status=404
        )

    estado_anterior = orden.estado

    if estado_anterior == nuevo_estado:
        return JsonResponse(
            {
                "ok": False,
                "error": "La orden ya tiene ese estado."
            },
            status=400
        )

    with transaction.atomic():

        orden.estado = nuevo_estado

        orden.save(
            update_fields=[
                "estado",
                "fecha_actualizacion",
            ]
        )

        HistorialEstado.objects.create(
            orden=orden,
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            usuario=request.user.username,
        )

    messages.success(
        request,
        f"Estado de {orden.tracking_id} guardado: "
        f"{orden.get_estado_display()}. "
        "El cliente aún no ha sido notificado.",
    )

    return redirect("panel_operaciones")


@login_required
def lista_clientes(request):

    from .models import Cliente

    clientes = Cliente.objects.all().order_by(
        "customer_number"
    )

    contexto = {
        "clientes": clientes,
    }

    return render(
        request,
        "operaciones/clientes.html",
        contexto
    )


@login_required
def detalle_cliente(request, customer_number):

    from .models import Cliente

    cliente = Cliente.objects.prefetch_related(
        "ordenes"
    ).get(
        customer_number=customer_number
    )

    ordenes = cliente.ordenes.all().order_by(
        "-fecha_creacion"
    )

    contexto = {
        "cliente": cliente,
        "ordenes": ordenes,
    }

    return render(
        request,
        "operaciones/detalle_cliente.html",
        contexto
    )
@login_required
def detalle_orden(request, tracking_id):

    orden = Orden.objects.select_related(
        "cliente"
    ).prefetch_related(
        "capturas"
    ).get(
        tracking_id=tracking_id
    )

    contexto = {
        "orden": orden,
    }

    return render(
        request,
        "operaciones/detalle_orden.html",
        contexto
    )
    


@login_required
def plantillas_correo(request):

    asegurar_plantillas()

    if request.method == "POST":
        for p in PlantillaCorreo.objects.all():
            p.asunto = (
                request.POST.get(f"asunto_{p.evento}", p.asunto).strip()
                or p.asunto
            )
            p.cuerpo = request.POST.get(f"cuerpo_{p.evento}", p.cuerpo)
            p.activa = request.POST.get(f"activa_{p.evento}") == "on"
            p.save()

        return redirect("/operaciones/plantillas-correo/?ok=1")

    contexto = {
        "plantillas": PlantillaCorreo.objects.order_by("id"),
        "variables": VARIABLES_DISPONIBLES,
        "guardado": request.GET.get("ok") == "1",
    }

    return render(request, "operaciones/plantillas_correo.html", contexto)


@login_required
def enviar_correo_prueba(request):

    if request.method == "POST":
        ok, mensaje = enviar_prueba()
        if ok:
            messages.success(request, mensaje)
        else:
            messages.error(request, mensaje)

    return redirect("configuracion_operaciones")


@login_required
@permission_required(
    "core.can_change_order_status",
    raise_exception=True
)
def notificar_cliente_estado(request):
    """
    Envía por correo al cliente el estado actual de su orden.
    Solo se ejecuta cuando el administrador pulsa el botón.
    """

    if request.method != "POST":
        return redirect("panel_operaciones")

    tracking_id = request.POST.get("tracking_id", "").strip()

    try:
        orden = Orden.objects.select_related("cliente").get(
            tracking_id=tracking_id
        )
    except Orden.DoesNotExist:
        messages.error(request, "Orden no encontrada.")
        return redirect("panel_operaciones")

    ok, mensaje = notificar_estado_manual(orden)

    if ok:
        messages.success(request, mensaje)
    else:
        messages.error(request, mensaje)

    return redirect("panel_operaciones")


# ============================================================
# CONFIGURACIÓN DEL SITIO (tarifas, precios, próxima salida, contacto)
# ============================================================

CAMPOS_PRECIO = [
    ("tarifa_menos_50", "Tarifa de 50 lb o menos"),
    ("tarifa_mas_50", "Tarifa de más de 50 lb"),
    ("tarifa_mixto", "Tarifa de paquete mezclado"),
    ("precio_celular", "Precio de celular"),
    ("precio_tablet", "Precio de iPad / tablet"),
    ("precio_laptop", "Precio de laptop"),
]


def _contar_correos_fallidos():
    return RegistroCorreo.objects.filter(
        estado=RegistroCorreo.Estado.FALLIDO,
        resuelto=False,
    ).count()


def _numero(valor, etiqueta):
    try:
        numero = Decimal(str(valor).replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"«{etiqueta}» no es un número válido.")

    if not numero.is_finite() or numero < 0 or numero >= 10000:
        raise ValueError(
            f"«{etiqueta}» debe estar entre 0 y 9999.99."
        )

    return numero.quantize(Decimal("0.01"))


def _texto_requerido(valor, etiqueta, maximo):
    valor = (valor or "").strip()

    if not valor:
        raise ValueError(f"«{etiqueta}» no puede quedar vacío.")

    if len(valor) > maximo:
        raise ValueError(f"«{etiqueta}» es demasiado largo.")

    return valor


def _correo(valor, etiqueta, requerido=False):
    valor = (valor or "").strip()

    if not valor:
        if requerido:
            raise ValueError(f"«{etiqueta}» no puede quedar vacío.")
        return ""

    try:
        validate_email(valor)
    except ValidationError:
        raise ValueError(f"«{etiqueta}» no es un correo válido.")

    return valor


def _telefono(valor, etiqueta):
    valor = _texto_requerido(valor, etiqueta, 40)
    digitos = re.sub(r"\D", "", valor)

    if not re.fullmatch(r"[0-9+()\-\s]+", valor) or not 8 <= len(digitos) <= 15:
        raise ValueError(
            f"«{etiqueta}» no parece un teléfono válido "
            "(usa números, +, espacios, paréntesis o guiones)."
        )

    return valor


@login_required
def configuracion_operaciones(request):

    configuracion = Configuracion.obtener()

    if request.method == "POST":

        try:
            # ---- precios y tarifas
            nuevos = {}
            for campo, etiqueta in CAMPOS_PRECIO:
                nuevos[campo] = _numero(request.POST.get(campo, ""), etiqueta)

            # ---- próxima salida (hora de Cuba)
            texto_fecha = request.POST.get("proximo_envio", "").strip()
            if texto_fecha:
                try:
                    fecha = datetime.strptime(texto_fecha, "%Y-%m-%dT%H:%M")
                except ValueError:
                    raise ValueError(
                        "La fecha y hora de la próxima salida no es válida."
                    )
                nuevos["proximo_envio"] = timezone.make_aware(fecha)
            else:
                nuevos["proximo_envio"] = None

            # ---- contacto público
            nuevos["contacto_email"] = _correo(
                request.POST.get("contacto_email"),
                "Correo de contacto",
                requerido=True,
            )
            nuevos["contacto_telefono_usa"] = _telefono(
                request.POST.get("contacto_telefono_usa"),
                "Teléfono de Estados Unidos",
            )
            nuevos["contacto_telefono_cuba"] = _telefono(
                request.POST.get("contacto_telefono_cuba"),
                "Teléfono de Cuba",
            )
            nuevos["contacto_whatsapp"] = _telefono(
                request.POST.get("contacto_whatsapp"),
                "WhatsApp",
            )

            direccion = _texto_requerido(
                request.POST.get("contacto_direccion"),
                "Dirección de recepción",
                300,
            )
            lineas = [l.strip() for l in direccion.splitlines() if l.strip()]
            if len(lineas) > 4:
                raise ValueError(
                    "La dirección de recepción puede tener como máximo 4 líneas."
                )
            nuevos["contacto_direccion"] = "\n".join(lineas)

            # ---- correos de notificación
            nuevos["email_admin"] = _correo(
                request.POST.get("email_admin"), "Correo que recibe los avisos"
            )
            nuevos["email_remitente"] = _correo(
                request.POST.get("email_remitente"), "Correo remitente"
            )
            nuevos["nombre_remitente"] = (
                request.POST.get("nombre_remitente", "").strip()[:100]
                or "KOCH ENVÍOS"
            )

        except ValueError as error:
            messages.error(request, f"No se guardó nada. {error}")
            return redirect("configuracion_operaciones")

        for campo, valor in nuevos.items():
            setattr(configuracion, campo, valor)

        configuracion.save()

        messages.success(
            request,
            "Configuración guardada. La página principal ya muestra los cambios.",
        )

        return redirect("configuracion_operaciones")

    proximo_input = ""
    if configuracion.proximo_envio:
        proximo_input = timezone.localtime(
            configuracion.proximo_envio
        ).strftime("%Y-%m-%dT%H:%M")

    contexto = {
        "configuracion": configuracion,
        # Como texto, para que el navegador reciba "5.99" y no "5,99"
        "valores": {
            campo: str(getattr(configuracion, campo))
            for campo, _ in CAMPOS_PRECIO
        },
        "proximo_envio_input": proximo_input,
        "correos_fallidos": _contar_correos_fallidos(),
    }

    return render(
        request,
        "operaciones/configuracion.html",
        contexto
    )


# ============================================================
# REGISTRO DE CORREOS (ver, reintentar, descartar)
# ============================================================

@login_required
def lista_correos(request):

    solo_fallidos = request.GET.get("filtro") == "fallidos"

    registros = RegistroCorreo.objects.all()

    if solo_fallidos:
        registros = registros.filter(
            estado=RegistroCorreo.Estado.FALLIDO,
            resuelto=False,
        )

    contexto = {
        "registros": registros[:200],
        "solo_fallidos": solo_fallidos,
        "correos_fallidos": _contar_correos_fallidos(),
    }

    return render(request, "operaciones/correos.html", contexto)


def _registro_desde_post(request):
    try:
        return RegistroCorreo.objects.get(
            pk=int(request.POST.get("registro_id", ""))
        )
    except (ValueError, RegistroCorreo.DoesNotExist):
        return None


@login_required
def reintentar_correo_panel(request):

    if request.method == "POST":
        registro = _registro_desde_post(request)

        if registro is None:
            messages.error(request, "Correo no encontrado.")
        else:
            ok, mensaje = reintentar_correo(registro)
            if ok:
                messages.success(request, mensaje)
            else:
                messages.error(request, mensaje)

    return redirect("/operaciones/correos/?filtro=fallidos")


@login_required
def descartar_correo_panel(request):

    if request.method == "POST":
        registro = _registro_desde_post(request)

        if registro is None:
            messages.error(request, "Correo no encontrado.")
        else:
            registro.resuelto = True
            registro.save(update_fields=["resuelto"])
            messages.success(request, "Correo descartado.")

    return redirect("/operaciones/correos/?filtro=fallidos")
