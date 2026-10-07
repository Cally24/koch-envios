import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction, models
from django.db.models import Q
from django.contrib.auth.decorators import login_required

from .notificaciones import notificar_registro, notificar_orden_creada
from .models import (
    Cliente,
    Orden,
    HistorialEstado,
    CapturaOrden,
    Configuracion,
    PushSubscription,
)



# ============================================================
# CLIENTES
# ============================================================

@csrf_exempt
def crear_orden(request):
    """
    Crea una nueva orden asociada a un cliente
    y guarda las capturas de pantalla enviadas.
    """

    if request.method != "POST":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    try:
        # ==========================================
        # DATOS DEL FORMULARIO
        # ==========================================

        customer_number = str(
            request.POST.get("customer_number", "")
        ).strip()

        tipo_orden = str(
            request.POST.get("tipo_orden", "compra_directa")
        ).strip()

        producto = str(
            request.POST.get("producto", "")
        ).strip()

        cantidad = request.POST.get("cantidad", 1)

        peso = request.POST.get("peso")

        notas = str(
            request.POST.get("notas", "")
        ).strip()


        # ==========================================
        # ENLACES
        # ==========================================

        enlaces = request.POST.getlist("enlaces[]")


        # ==========================================
        # CAPTURAS
        # ==========================================

        capturas = request.FILES.getlist("capturas")


        # ==========================================
        # VALIDACIONES
        # ==========================================

        if not customer_number:
            return JsonResponse(
                {"error": "El Customer Number es obligatorio."},
                status=400
            )

        if not producto:
            return JsonResponse(
                {"error": "El producto es obligatorio."},
                status=400
            )

        if tipo_orden not in (
            "compra_directa",
            "compra_asistida"
        ):
            return JsonResponse(
                {"error": "El tipo de orden no es válido."},
                status=400
            )

        try:
            cantidad = int(cantidad)
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "La cantidad no es válida."},
                status=400
            )

        if cantidad <= 0:
            return JsonResponse(
                {"error": "La cantidad debe ser mayor que cero."},
                status=400
            )


        # ==========================================
        # PESO
        # ==========================================

        if peso in ("", None):
            peso = None
        else:
            try:
                peso = float(peso)
            except (ValueError, TypeError):
                return JsonResponse(
                    {"error": "El peso no es válido."},
                    status=400
                )

            if peso < 0:
                return JsonResponse(
                    {"error": "El peso no puede ser negativo."},
                    status=400
                )


        # ==========================================
        # VALIDAR CAPTURAS
        # ==========================================

        if not capturas:
            return JsonResponse(
                {
                    "error":
                    "Debes adjuntar al menos una captura de pantalla."
                },
                status=400
            )


        # ==========================================
        # BUSCAR CLIENTE
        # ==========================================

        try:
            cliente = Cliente.objects.get(
                customer_number=customer_number,
                activo=True
            )

        except Cliente.DoesNotExist:
            return JsonResponse(
                {
                    "error":
                    "Customer Number no encontrado."
                },
                status=404
            )


        # ==========================================
        # CREAR ORDEN
        # ==========================================

        with transaction.atomic():

            orden = Orden.objects.create(
                cliente=cliente,
                producto=producto,
                cantidad=cantidad,
                peso=peso,
                estado="recibida",
                tipo=(
                    "asistida"
                    if tipo_orden == "compra_asistida"
                    else "directa"
                ),
                observaciones=notas,
            )


            # ======================================
            # TRACKING ID
            # ======================================

            tracking_id = generar_tracking_id(
                orden.id
            )

            orden.tracking_id = tracking_id

            orden.save(
                update_fields=["tracking_id"]
            )


            # ======================================
            # GUARDAR CAPTURAS
            # ======================================

            for archivo in capturas:

                CapturaOrden.objects.create(
                    orden=orden,
                    archivo=archivo
                )


            # ======================================
            # HISTORIAL
            # ======================================

            HistorialEstado.objects.create(
                orden=orden,
                estado_anterior=None,
                estado_nuevo="recibida",
                nota="Orden creada",
                usuario="sistema",
            )


        notificar_orden_creada(orden)

        # ==========================================
        # RESPUESTA
        # ==========================================

        return JsonResponse(
            {
                "mensaje":
                    "Orden creada correctamente.",

                "tracking_id":
                    orden.tracking_id,

                "orden": {

                    "id":
                        orden.id,

                    "tracking_id":
                        orden.tracking_id,

                    "customer_number":
                        cliente.customer_number,

                    "cliente":
                        f"{cliente.nombre} "
                        f"{cliente.apellidos}",

                    "producto":
                        orden.producto,

                    "cantidad":
                        orden.cantidad,

                    "peso":
                        (
                            str(orden.peso)
                            if orden.peso is not None
                            else None
                        ),

                    "estado":
                        orden.estado,

                    "tipo":
                        orden.tipo,

                    "capturas":
                        len(capturas),

                },
            },
            status=201
        )


    except Exception as e:

        return JsonResponse(
            {
                "error": str(e)
            },
            status=500
        )


def generar_tracking_id(orden_id):
    """
    Genera un Tracking ID único.

    Formato:
    KCH-YYMMDD-0001
    """

    from django.utils import timezone

    fecha = timezone.localdate()

    return (
        f"KCH-{fecha.strftime('%y%m%d')}-"
        f"{orden_id:04d}"
    )


# ============================================================
# TRACKING
# ============================================================

def buscar_tracking(request):
    """
    Busca una orden mediante su Tracking ID.
    """

    if request.method != "GET":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    tracking_id = request.GET.get(
        "tracking_id",
        ""
    ).strip().upper()

    if not tracking_id:
        return JsonResponse(
            {"error": "Debes introducir un Tracking ID."},
            status=400
        )

    try:
        orden = Orden.objects.select_related(
            "cliente"
        ).get(
            tracking_id=tracking_id
        )

    except Orden.DoesNotExist:
        return JsonResponse(
            {
                "error": "No se encontró ninguna orden con ese Tracking ID."
            },
            status=404
        )

    historial = HistorialEstado.objects.filter(
        orden=orden
    ).order_by("fecha")

    historial_data = []

    for item in historial:
        historial_data.append(
            {
                "id": item.id,
                "estado_anterior": item.estado_anterior,
                "estado_nuevo": item.estado_nuevo,
                "nota": item.nota,
                "usuario": item.usuario,
                "fecha": item.fecha,
                "orden": orden.id,
            }
        )

    return JsonResponse(
        {
            "id": orden.id,
            "tracking_id": orden.tracking_id,
            "tipo": orden.tipo,
            "producto": orden.producto,
            "cantidad": orden.cantidad,
            "peso": (
                str(orden.peso)
                if orden.peso is not None
                else None
            ),
            "precio": (
                str(orden.precio)
                if orden.precio is not None
                else None
            ),
            "estado": orden.estado,

            "cliente": orden.cliente.id,
            "cliente_customer_number": (
                orden.cliente.customer_number
            ),
            "cliente_nombre": (
                f"{orden.cliente.nombre} "
                f"{orden.cliente.apellidos}"
            ),

            "destinatario_nombre": (
                orden.destinatario_nombre
            ),
            "destinatario_telefono": (
                orden.destinatario_telefono
            ),
            "destinatario_direccion": (
                orden.destinatario_direccion
            ),

            "observaciones": orden.observaciones,
            "notas_internas": orden.notas_internas,

            "fecha_creacion": orden.fecha_creacion,
            "fecha_actualizacion": orden.fecha_actualizacion,

            "historial": historial_data,

            "notas": [],
        }
    )
    
# ============================================================
# CAMBIAR ESTADO DE ORDEN
# ============================================================

@csrf_exempt
def cambiar_estado_orden(request):
    """
    Cambia el estado de una orden y registra automáticamente
    el cambio en el historial.
    """

    if request.method != "POST":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    try:
        datos = json.loads(request.body)

        tracking_id = str(
            datos.get("tracking_id", "")
        ).strip().upper()

        nuevo_estado = str(
            datos.get("estado", "")
        ).strip().lower()

        nota = str(
            datos.get("nota", "")
        ).strip()

        usuario = str(
            datos.get("usuario", "admin")
        ).strip()

        # --------------------------------------------
        # Validaciones
        # --------------------------------------------

        if not tracking_id:
            return JsonResponse(
                {"error": "El Tracking ID es obligatorio."},
                status=400
            )

        if not nuevo_estado:
            return JsonResponse(
                {"error": "El nuevo estado es obligatorio."},
                status=400
            )

        estados_validos = [
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
        ]

        if nuevo_estado not in estados_validos:
            return JsonResponse(
                {
                    "error": "Estado no válido.",
                    "estados_validos": estados_validos,
                },
                status=400
            )

        # --------------------------------------------
        # Buscar orden
        # --------------------------------------------

        try:
            orden = Orden.objects.get(
                tracking_id=tracking_id
            )
        except Orden.DoesNotExist:
            return JsonResponse(
                {
                    "error": "No se encontró ninguna orden con ese Tracking ID."
                },
                status=404
            )

        estado_anterior = orden.estado

        # --------------------------------------------
        # Evitar cambios innecesarios
        # --------------------------------------------

        if estado_anterior == nuevo_estado:
            return JsonResponse(
                {
                    "error": "La orden ya tiene ese estado.",
                    "estado": orden.estado,
                },
                status=400
            )

        # --------------------------------------------
        # Actualizar orden + historial
        # --------------------------------------------

        with transaction.atomic():

            orden.estado = nuevo_estado
            orden.save(update_fields=["estado"])

            HistorialEstado.objects.create(
                orden=orden,
                estado_anterior=estado_anterior,
                estado_nuevo=nuevo_estado,
                nota=nota or "Estado actualizado",
                usuario=usuario or "admin",
            )

        return JsonResponse(
            {
                "mensaje": "Estado actualizado correctamente.",
                "tracking_id": orden.tracking_id,
                "estado_anterior": estado_anterior,
                "estado_nuevo": orden.estado,
                "nota": nota or "Estado actualizado",
                "usuario": usuario or "admin",
            },
            status=200
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "El JSON enviado no es válido."},
            status=400
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )
        # ============================================================
# CLIENTES - REGISTRO
# ============================================================

@csrf_exempt
def registrar_cliente(request):
    """
    Registra un nuevo cliente y genera automáticamente
    su Customer Number.
    """

    if request.method != "POST":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    try:
        nombre = str(request.POST.get("nombre", "")).strip()
        apellidos = str(request.POST.get("apellidos", "")).strip()
        telefono = str(request.POST.get("telefono", "")).strip()
        whatsapp = str(request.POST.get("whatsapp", "")).strip()
        email = str(request.POST.get("email", "")).strip()
        direccion = str(request.POST.get("direccion", "")).strip()
        ciudad = str(request.POST.get("ciudad", "")).strip()
        provincia = str(request.POST.get("provincia", "")).strip()
        direccion_entrega = str(
            request.POST.get("direccion_entrega", "")
        ).strip()
        instrucciones_entrega = str(
            request.POST.get("instrucciones_entrega", "")
        ).strip()

        campos_obligatorios = {
            "nombre": nombre,
            "apellidos": apellidos,
            "telefono": telefono,
            "email": email,
            "direccion": direccion,
            "ciudad": ciudad,
            "provincia": provincia,
        }

        for campo, valor in campos_obligatorios.items():
            if not valor:
                return JsonResponse(
                    {
                        "error": f"El campo '{campo}' es obligatorio."
                    },
                    status=400
                )

        with transaction.atomic():

            ultimo_cliente = (
                Cliente.objects
                .select_for_update()
                .order_by("-customer_number")
                .first()
            )

            if ultimo_cliente:
                siguiente_numero = (
                    ultimo_cliente.customer_number + 1
                )
            else:
                siguiente_numero = 231

            cliente = Cliente.objects.create(
                customer_number=siguiente_numero,
                nombre=nombre,
                apellidos=apellidos,
                telefono=telefono,
                whatsapp=whatsapp,
                email=email,
                direccion=direccion,
                ciudad=ciudad,
                provincia=provincia,
                direccion_entrega=direccion_entrega,
                instrucciones_entrega=instrucciones_entrega,
                activo=True,
            )

        notificar_registro(cliente)

        return JsonResponse(
            {
                "mensaje": "Cliente registrado correctamente.",
                "customer_number": cliente.customer_number,
                "cliente": {
                    "id": cliente.id,
                    "customer_number": cliente.customer_number,
                    "nombre": cliente.nombre,
                    "apellidos": cliente.apellidos,
                    "telefono": cliente.telefono,
                    "whatsapp": cliente.whatsapp,
                    "email": cliente.email,
                    "direccion": cliente.direccion,
                    "ciudad": cliente.ciudad,
                    "provincia": cliente.provincia,
                    "direccion_entrega": cliente.direccion_entrega,
                    "instrucciones_entrega": cliente.instrucciones_entrega,
                    "activo": cliente.activo,
                    "fecha_registro": cliente.fecha_registro,
                    "fecha_actualizacion": cliente.fecha_actualizacion,
                },
            },
            status=201
        )

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


# ============================================================
# CLIENTES - BÚSQUEDA
# ============================================================

def buscar_cliente(request):
    """
    Busca un cliente mediante su Customer Number.
    """

    if request.method != "GET":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    customer_number = str(
        request.GET.get("customer_number", "")
    ).strip()

    if not customer_number:
        return JsonResponse(
            {
                "error": "Debes introducir un Customer Number."
            },
            status=400
        )

    try:
        customer_number = int(customer_number)
    except (ValueError, TypeError):
        return JsonResponse(
            {
                "error": "El Customer Number no es válido."
            },
            status=400
        )

    try:
        cliente = Cliente.objects.get(
            customer_number=customer_number,
            activo=True
        )

    except Cliente.DoesNotExist:
        return JsonResponse(
            {
                "error": (
                    "No se encontró ningún cliente "
                    "con ese Customer Number."
                )
            },
            status=404
        )

    return JsonResponse(
        {
            "id": cliente.id,
            "customer_number": cliente.customer_number,
            "nombre": cliente.nombre,
            "apellidos": cliente.apellidos,
            "telefono": cliente.telefono,
            "whatsapp": cliente.whatsapp,
            "email": cliente.email,
            "direccion": cliente.direccion,
            "ciudad": cliente.ciudad,
            "provincia": cliente.provincia,
            "direccion_entrega": cliente.direccion_entrega,
            "instrucciones_entrega": cliente.instrucciones_entrega,
            "activo": cliente.activo,
            "fecha_registro": cliente.fecha_registro,
            "fecha_actualizacion": cliente.fecha_actualizacion,
        },
        status=200
    )

# ============================================================
# CONFIGURACIÓN DEL SITIO
# ============================================================

def obtener_configuracion(request):
    """
    Devuelve la configuración pública del sitio: tarifas, precios de
    electrónicos, próxima salida y datos de contacto.
    """

    if request.method != "GET":
        return JsonResponse(
            {"error": "Método no permitido."},
            status=405
        )

    c = Configuracion.obtener()

    return JsonResponse(
        {
            "proximo_envio": (
                c.proximo_envio.isoformat()
                if c.proximo_envio
                else None
            ),

            "tarifa_menos_50": str(c.tarifa_menos_50),
            "tarifa_mas_50": str(c.tarifa_mas_50),
            "tarifa_mixto": str(c.tarifa_mixto),

            "precio_celular": str(c.precio_celular),
            "precio_tablet": str(c.precio_tablet),
            "precio_laptop": str(c.precio_laptop),

            "contacto": {
                "email": c.contacto_email,
                "telefono_usa": c.contacto_telefono_usa,
                "telefono_cuba": c.contacto_telefono_cuba,
                "whatsapp": c.contacto_whatsapp,
                "direccion": c.contacto_direccion,
            },
        },
        status=200
    )


# ============================================================
# PUSH NOTIFICATIONS
# ============================================================

@csrf_exempt
@login_required
def guardar_suscripcion_push(request):

    if request.method != "POST":
        return JsonResponse(
            {
                "ok": False,
                "error": "Método no permitido",
            },
            status=405,
        )

    try:
        datos = json.loads(request.body)

        endpoint = datos.get("endpoint")
        keys = datos.get("keys", {})

        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not endpoint or not p256dh or not auth:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Datos de suscripción incompletos",
                },
                status=400,
            )

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                "p256dh": p256dh,
                "auth": auth,
                "usuario": request.user,
                "activa": True,
            },
        )

        return JsonResponse(
            {
                "ok": True,
                "mensaje": "Suscripción Push guardada correctamente",
            }
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {
                "ok": False,
                "error": "JSON inválido",
            },
            status=400,
        )
# ============================================================
# SERVICE WORKER
# ============================================================

from django.http import HttpResponse
from django.conf import settings
from pathlib import Path


def service_worker(request):

    archivo = (
        Path(settings.BASE_DIR)
        / "core"
        / "static"
        / "sw.js"
    )

    contenido = archivo.read_text(
        encoding="utf-8"
    )

    return HttpResponse(
        contenido,
        content_type="application/javascript",
    )