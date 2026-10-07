"""
core/notificaciones.py

Envío de correos de KOCH ENVÍOS con plantillas editables desde
/operaciones/plantillas-correo/.

Reglas:
- Un fallo de correo NUNCA debe romper el registro ni la orden.
- Los correos se envían en un hilo aparte para no hacer esperar al cliente.
- Las plantillas se crean solas con un texto por defecto la primera vez.
"""

import logging
import re
import threading
import time

from django.conf import settings
from django.db import connection
from django.core.mail import send_mail
from django.utils import timezone
from email.utils import formataddr

from .models import Configuracion, PlantillaCorreo, RegistroCorreo

logger = logging.getLogger(__name__)


# ============================================================
# TEXTOS POR DEFECTO (el admin los puede cambiar desde el panel)
# ============================================================

PLANTILLAS_POR_DEFECTO = {
    "registro_cliente": {
        "asunto": "Bienvenido a KOCH ENVÍOS - Tu ID de cliente es {customer_number}",
        "cuerpo": (
            "Hola {nombre},\n\n"
            "¡Gracias por registrarte en KOCH ENVÍOS!\n\n"
            "Tu ID de cliente es: {customer_number}\n\n"
            "Guárdalo: lo necesitarás cada vez que crees una orden.\n\n"
            "Saludos,\n"
            "Equipo KOCH ENVÍOS"
        ),
    },
    "orden_creada_cliente": {
        "asunto": "Recibimos tu orden {tracking_id}",
        "cuerpo": (
            "Hola {nombre},\n\n"
            "Hemos recibido tu orden.\n\n"
            "Tracking ID: {tracking_id}\n"
            "Tipo de orden: {tipo}\n"
            "Producto: {producto}\n"
            "Cantidad: {cantidad}\n"
            "Estado: {estado}\n\n"
            "Te avisaremos por este medio cada vez que cambie su estado.\n\n"
            "Saludos,\n"
            "Equipo KOCH ENVÍOS"
        ),
    },
    "orden_creada_admin": {
        "asunto": "Nueva orden {tipo}: {tracking_id}",
        "cuerpo": (
            "Se creó una nueva orden.\n\n"
            "Tracking ID: {tracking_id}\n"
            "Tipo: {tipo}\n"
            "Cliente: #{customer_number} - {nombre} {apellidos}\n"
            "Email: {email}\n"
            "Teléfono: {telefono}\n"
            "Producto: {producto}\n"
            "Cantidad: {cantidad}\n"
        ),
    },
    "estado_actualizado": {
        "asunto": "Tu orden {tracking_id} cambió a: {estado}",
        "cuerpo": (
            "Hola {nombre},\n\n"
            "El estado de tu orden {tracking_id} ({producto}) ha cambiado.\n\n"
            "Estado anterior: {estado_anterior}\n"
            "Estado actual: {estado}\n\n"
            "Saludos,\n"
            "Equipo KOCH ENVÍOS"
        ),
    },
}

# Variables que el admin puede usar en los textos (se muestran en el panel)
VARIABLES_DISPONIBLES = [
    "nombre", "apellidos", "email", "telefono", "customer_number",
    "tracking_id", "tipo", "producto", "cantidad", "peso",
    "estado", "estado_anterior",
]


# ============================================================
# UTILIDADES INTERNAS
# ============================================================

def asegurar_plantillas():
    """Crea las plantillas que falten con el texto por defecto."""
    for evento, datos in PLANTILLAS_POR_DEFECTO.items():
        PlantillaCorreo.objects.get_or_create(
            evento=evento,
            defaults={"asunto": datos["asunto"], "cuerpo": datos["cuerpo"]},
        )


def _render(texto, contexto):
    """
    Reemplaza {variable} por su valor. Si la variable no existe se deja
    tal cual, y las llaves sueltas no rompen nada (no usa str.format).
    """
    return re.sub(
        r"\{(\w+)\}",
        lambda m: str(contexto.get(m.group(1), m.group(0))),
        texto,
    )


def _remitente():
    """
    Remitente configurado en el panel (Nombre <correo>).
    Si no hay uno, usa DEFAULT_FROM_EMAIL de settings.
    """
    try:
        conf = Configuracion.obtener()
        if conf.email_remitente:
            nombre = (conf.nombre_remitente or "KOCH ENVÍOS")
            nombre = nombre.replace("\r", " ").replace("\n", " ").strip()
            return formataddr((nombre, conf.email_remitente))
    except Exception:
        logger.exception("No se pudo leer el remitente configurado")
    return settings.DEFAULT_FROM_EMAIL


def _email_admin():
    try:
        email = Configuracion.obtener().email_admin
    except Exception:
        email = ""
    return email or getattr(settings, "ADMIN_NOTIFY_EMAIL", "")


def _contexto_cliente(cliente):
    return {
        "nombre": cliente.nombre,
        "apellidos": cliente.apellidos,
        "email": cliente.email,
        "telefono": cliente.telefono,
        "customer_number": cliente.customer_number,
    }


def _contexto_orden(orden, estado_anterior=""):
    contexto = _contexto_cliente(orden.cliente)
    contexto.update({
        "tracking_id": orden.tracking_id,
        "tipo": orden.get_tipo_display(),
        "producto": orden.producto,
        "cantidad": orden.cantidad,
        "peso": orden.peso if orden.peso is not None else "—",
        "estado": orden.get_estado_display(),
        "estado_anterior": estado_anterior,
    })
    return contexto


# ============================================================
# ENVÍO Y REGISTRO
# ============================================================

def _resolver_fallos_previos(registro):
    """Si este correo salió bien, los fallos anteriores iguales dejan de ser pendientes."""
    RegistroCorreo.objects.filter(
        estado=RegistroCorreo.Estado.FALLIDO,
        resuelto=False,
        evento=registro.evento,
        destinatario=registro.destinatario,
        referencia=registro.referencia,
    ).exclude(pk=registro.pk).update(resuelto=True)


def _intentar_envio(registro, remitente, intentos=1):
    """
    Envía el correo guardado en `registro` y deja anotado el resultado.
    Los fallos de conexión suelen ser momentáneos, por eso se puede
    reintentar. Devuelve (ok, error).
    """
    ultimo_error = ""

    for numero in range(1, intentos + 1):
        registro.intentos += 1

        try:
            send_mail(
                subject=registro.asunto,
                message=registro.cuerpo,
                from_email=remitente,
                recipient_list=[registro.destinatario],
                fail_silently=False,
            )
        except Exception as error:
            ultimo_error = f"{type(error).__name__}: {error}"
            logger.warning(
                "Fallo al enviar a %s (intento %s de %s): %s",
                registro.destinatario, numero, intentos, ultimo_error,
            )
            if numero < intentos:
                time.sleep(5)
            continue

        registro.estado = RegistroCorreo.Estado.ENVIADO
        registro.error = ""
        registro.resuelto = True
        registro.fecha_envio = timezone.now()
        registro.save()
        _resolver_fallos_previos(registro)
        return True, ""

    registro.estado = RegistroCorreo.Estado.FALLIDO
    registro.error = ultimo_error[:1000]
    registro.resuelto = False
    registro.save()
    logger.error(
        "No se pudo enviar el correo a %s tras %s intento(s)",
        registro.destinatario, intentos,
    )
    return False, ultimo_error


def _enviar_en_hilo(registro_id, remitente):
    try:
        registro = RegistroCorreo.objects.get(pk=registro_id)
        _intentar_envio(registro, remitente, intentos=3)
    except Exception:
        logger.exception("Error inesperado enviando el correo %s", registro_id)
    finally:
        connection.close()


def enviar_notificacion(evento, destinatario, contexto, referencia=""):
    """Envío automático en segundo plano. Queda registrado en el panel."""
    if not destinatario:
        return

    asegurar_plantillas()
    plantilla = PlantillaCorreo.objects.get(evento=evento)

    if not plantilla.activa:
        return

    # Sin saltos de línea en el asunto (evita errores de cabecera)
    asunto = _render(plantilla.asunto, contexto).replace("\r", " ").replace("\n", " ")
    cuerpo = _render(plantilla.cuerpo, contexto)

    registro = RegistroCorreo.objects.create(
        evento=evento,
        destinatario=destinatario,
        asunto=asunto[:200],
        cuerpo=cuerpo,
        referencia=referencia,
        estado=RegistroCorreo.Estado.PENDIENTE,
    )

    threading.Thread(
        target=_enviar_en_hilo,
        args=(registro.pk, _remitente()),
        daemon=True,
    ).start()


# ============================================================
# FUNCIONES PÚBLICAS (las que se llaman desde las vistas)
# ============================================================

def notificar_registro(cliente):
    """Correo de bienvenida con el ID de cliente."""
    try:
        enviar_notificacion(
            "registro_cliente",
            cliente.email,
            _contexto_cliente(cliente),
            referencia=str(cliente.customer_number),
        )
    except Exception:
        logger.exception("Error en notificar_registro")


def notificar_orden_creada(orden):
    """Un correo al cliente y otro al administrador."""
    try:
        contexto = _contexto_orden(orden)
        enviar_notificacion(
            "orden_creada_cliente", orden.cliente.email, contexto,
            referencia=orden.tracking_id,
        )
        enviar_notificacion(
            "orden_creada_admin", _email_admin(), contexto,
            referencia=orden.tracking_id,
        )
    except Exception:
        logger.exception("Error en notificar_orden_creada")


def notificar_estado_manual(orden):
    """
    Envía al cliente el correo con el estado ACTUAL de la orden.
    Se usa desde el botón "Notificar al cliente" del panel.

    Es un envío directo (sin hilo) para poder confirmar al administrador
    si salió bien o no. Devuelve (ok, mensaje).
    """
    try:
        destinatario = orden.cliente.email
        if not destinatario:
            return False, "El cliente no tiene correo registrado."

        asegurar_plantillas()
        plantilla = PlantillaCorreo.objects.get(evento="estado_actualizado")

        if not plantilla.activa:
            return False, (
                "El correo de cambio de estado está desactivado. "
                "Actívalo en «Editar los textos de los correos»."
            )

        # "Estado anterior" = el último estado del que se avisó al cliente.
        # Si nunca se le avisó, el cliente solo conoce "Recibida" (la creación).
        codigo_anterior = orden.estado_notificado or "recibida"
        anterior = dict(orden.Estado.choices).get(codigo_anterior, codigo_anterior)

        contexto = _contexto_orden(orden, estado_anterior=anterior)

        asunto = (
            _render(plantilla.asunto, contexto)
            .replace("\r", " ")
            .replace("\n", " ")
        )
        cuerpo = _render(plantilla.cuerpo, contexto)

        registro = RegistroCorreo.objects.create(
            evento="estado_actualizado",
            destinatario=destinatario,
            asunto=asunto[:200],
            cuerpo=cuerpo,
            referencia=orden.tracking_id,
            estado=RegistroCorreo.Estado.PENDIENTE,
        )

        ok, error = _intentar_envio(registro, _remitente(), intentos=1)

        if not ok:
            return False, f"No se pudo enviar el correo: {error}"

    except Exception as error:
        logger.exception("Falló la notificación manual de estado")
        return False, f"No se pudo enviar el correo: {error}"

    orden.estado_notificado = orden.estado
    orden.fecha_notificacion = timezone.now()
    orden.save(update_fields=["estado_notificado", "fecha_notificacion"])

    return True, (
        f"Correo enviado a {destinatario} "
        f"(orden {orden.tracking_id}, estado: {orden.get_estado_display()})."
    )


def reintentar_correo(registro):
    """Vuelve a enviar un correo que había fallado. Devuelve (ok, mensaje)."""
    ok, error = _intentar_envio(registro, _remitente(), intentos=1)

    if ok:
        return True, f"Correo reenviado a {registro.destinatario}."

    return False, f"Sigue sin poder enviarse a {registro.destinatario}: {error}"


def enviar_prueba():
    """
    Envía un correo de prueba (sin hilo) al correo del administrador
    usando el remitente configurado. Devuelve (ok, mensaje).
    """
    destinatario = _email_admin()
    if not destinatario:
        return False, "Primero guarda el correo que recibe los avisos."

    try:
        send_mail(
            subject="Prueba de correo - KOCH ENVÍOS",
            message=(
                "Este es un correo de prueba.\n\n"
                "Si lo recibes, las notificaciones están bien configuradas."
            ),
            from_email=_remitente(),
            recipient_list=[destinatario],
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("Falló el correo de prueba")
        return False, f"No se pudo enviar: {error}"

    return True, f"Correo de prueba enviado a {destinatario}."
