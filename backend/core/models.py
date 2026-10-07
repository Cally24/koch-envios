from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings


# ============================================================
# CLIENTES
# ============================================================

class Cliente(models.Model):
    customer_number = models.PositiveIntegerField(
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Customer Number",
    )

    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)

    telefono = models.CharField(max_length=30)
    whatsapp = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    email = models.EmailField()

    direccion = models.TextField()
    ciudad = models.CharField(max_length=100)
    provincia = models.CharField(max_length=100)

    direccion_entrega = models.TextField(
        blank=True,
        default="",
    )

    instrucciones_entrega = models.TextField(
        blank=True,
        default="",
    )

    activo = models.BooleanField(default=True)

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["customer_number"]
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return f"{self.customer_number} - {self.nombre} {self.apellidos}"


# ============================================================
# ÓRDENES
# ============================================================

class Orden(models.Model):

    class TipoOrden(models.TextChoices):
        DIRECTA = "directa", "Directa"
        ASISTIDA = "asistida", "Asistida"

    class Estado(models.TextChoices):
        RECIBIDA = "recibida", "Recibida"
        REVISION = "revision", "En revisión"
        INFO_REQUERIDA = "info_requerida", "Información requerida"
        CONFIRMADA = "confirmada", "Confirmada"
        PAGO_PENDIENTE = "pago_pendiente", "Pago pendiente"
        PAGO_RECIBIDO = "pago_recibido", "Pago recibido"
        PREPARANDO = "preparando", "Preparando envío"
        TRANSITO = "transito", "En tránsito"
        CUBA = "cuba", "Llegó a Cuba"
        DISPONIBLE = "disponible", "Disponible para entrega"
        ENTREGADA = "entregada", "Entregada"
        CANCELADA = "cancelada", "Cancelada"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name="ordenes",
        verbose_name="Cliente",
    )

    tracking_id = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True,
        verbose_name="Tracking ID",
    )

    tipo = models.CharField(
        max_length=20,
        choices=TipoOrden.choices,
        default=TipoOrden.DIRECTA,
    )

    producto = models.CharField(
        max_length=255
    )

    cantidad = models.PositiveIntegerField(
        default=1,
        validators=[
            MinValueValidator(1)
        ],
    )

    peso = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0)
        ],
    )

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0)
        ],
    )

    estado = models.CharField(
        max_length=30,
        choices=Estado.choices,
        default=Estado.RECIBIDA,
        db_index=True,
    )

    destinatario_nombre = models.CharField(
        max_length=150,
        blank=True,
        default="",
    )

    destinatario_telefono = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    destinatario_direccion = models.TextField(
        blank=True,
        default="",
    )

    observaciones = models.TextField(
        blank=True,
        default="",
    )

    notas_internas = models.TextField(
        blank=True,
        default="",
    )

    # Último estado del que se avisó al cliente por correo
    estado_notificado = models.CharField(
        max_length=30,
        blank=True,
        default="",
    )

    fecha_notificacion = models.DateTimeField(
        null=True,
        blank=True,
    )

    fecha_creacion = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Orden"
        verbose_name_plural = "Órdenes"

    def __str__(self):
        return f"{self.tracking_id} - Cliente {self.cliente.customer_number}"


# ============================================================
# HISTORIAL DE ESTADOS
# ============================================================

class HistorialEstado(models.Model):

    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name="Orden",
    )

    estado_anterior = models.CharField(
        max_length=30,
        choices=Orden.Estado.choices,
        null=True,
        blank=True,
    )

    estado_nuevo = models.CharField(
        max_length=30,
        choices=Orden.Estado.choices,
    )

    nota = models.TextField(
        blank=True,
        default="",
    )

    usuario = models.CharField(
        max_length=150,
        default="sistema",
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["fecha"]
        verbose_name = "Historial de estado"
        verbose_name_plural = "Historial de estados"

    def __str__(self):
        return (
            f"{self.orden.tracking_id} - "
            f"{self.estado_nuevo}"
        )


# ============================================================
# NOTAS DE ORDEN
# ============================================================

class NotaOrden(models.Model):

    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="notas",
        verbose_name="Orden",
    )

    texto = models.TextField()

    usuario = models.CharField(
        max_length=150,
        default="sistema",
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Nota de orden"
        verbose_name_plural = "Notas de órdenes"

    def __str__(self):
        return (
            f"Nota {self.orden.tracking_id} - "
            f"{self.fecha:%Y-%m-%d %H:%M}"
        )
class CapturaOrden(models.Model):

    orden = models.ForeignKey(
        Orden,
        on_delete=models.CASCADE,
        related_name="capturas",
        verbose_name="Orden",
    )

    archivo = models.ImageField(
        upload_to="ordenes/capturas/"
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Captura - {self.orden.tracking_id}"
        )

# ============================================================
# CONFIGURACIÓN DEL SITIO
# ============================================================

class Configuracion(models.Model):

    proximo_envio = models.DateTimeField(
        verbose_name="Próxima salida programada",
        null=True,
        blank=True,
    )

    # ========================================================
    # TARIFAS DE ENVÍO
    # ========================================================

    tarifa_menos_50 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=5.99,
        verbose_name="Tarifa paquetes menores de 50 lb",
    )

    tarifa_mas_50 = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=4.99,
        verbose_name="Tarifa paquetes mayores de 50 lb",
    )

    # ========================================================
    # PRECIOS DE ELECTRÓNICOS
    # ========================================================

    precio_celular = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=50.00,
        verbose_name="Precio celular",
    )

    precio_tablet = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=55.00,
        verbose_name="Precio iPad / Tablet",
    )

    precio_laptop = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=75.00,
        verbose_name="Precio laptop",
    )

    tarifa_mixto = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=6.00,
        verbose_name="Tarifa paquetes mezclados (por lb)",
    )

    # ========================================================
    # CONTACTO PÚBLICO (página principal)
    # ========================================================

    contacto_email = models.EmailField(
        blank=True,
        default="kochenvios@gmail.com",
        verbose_name="Correo de contacto (página principal)",
    )

    contacto_telefono_usa = models.CharField(
        max_length=40,
        blank=True,
        default="+1 (813) 255-6899",
        verbose_name="Teléfono de Estados Unidos",
    )

    contacto_telefono_cuba = models.CharField(
        max_length=40,
        blank=True,
        default="+53 59307450",
        verbose_name="Teléfono de Cuba",
    )

    contacto_whatsapp = models.CharField(
        max_length=40,
        blank=True,
        default="+53 59307450",
        verbose_name="WhatsApp",
    )

    contacto_direccion = models.TextField(
        blank=True,
        default="8417 N Armenia Ave, Apto 827\nTampa, Florida 33604-2691\nEstados Unidos",
        verbose_name="Dirección de recepción en Estados Unidos",
    )

    email_admin = models.EmailField(
        blank=True,
        default="",
        verbose_name="Correo que recibe los avisos (administrador)",
    )

    email_remitente = models.EmailField(
        blank=True,
        default="",
        verbose_name="Correo desde el que se envían las notificaciones",
    )

    nombre_remitente = models.CharField(
        max_length=100,
        blank=True,
        default="KOCH ENVÍOS",
        verbose_name="Nombre del remitente",
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )
    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"

    def __str__(self):
        return "Configuración general"

    @classmethod
    def obtener(cls):
        """Devuelve siempre la misma fila de configuración (la primera)."""
        return cls.objects.order_by("pk").first() or cls.objects.create()
    # ========================================================
    # NOTIFICACIONES
    # ========================================================

    notificaciones_push_activas = models.BooleanField(
        default=True,
        verbose_name="Notificaciones Push activas",
    )

    notificar_nuevo_cliente = models.BooleanField(
        default=True,
        verbose_name="Notificar nuevo cliente",
    )

    notificar_nueva_orden = models.BooleanField(
        default=True,
        verbose_name="Notificar nueva orden",
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración"
# ============================================================
# SUSCRIPCIONES PUSH
# ============================================================

class PushSubscription(models.Model):

    endpoint = models.TextField(
        unique=True,
        verbose_name="Endpoint Push",
    )

    p256dh = models.TextField(
        verbose_name="Clave pública del navegador",
    )

    auth = models.TextField(
        verbose_name="Clave de autenticación",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Usuario",
    )

    activa = models.BooleanField(
        default=True,
        verbose_name="Suscripción activa",
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True,
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "Suscripción Push"
        verbose_name_plural = "Suscripciones Push"

    def __str__(self):
        return f"Push - {self.usuario.username}"


# ============================================================
# PLANTILLAS DE CORREO (editables desde /operaciones/)
# ============================================================

class PlantillaCorreo(models.Model):

    class Evento(models.TextChoices):
        REGISTRO = "registro_cliente", "Registro de cliente (al cliente)"
        ORDEN_CLIENTE = "orden_creada_cliente", "Orden creada (al cliente)"
        ORDEN_ADMIN = "orden_creada_admin", "Orden creada (al administrador)"
        ESTADO = "estado_actualizado", "Cambio de estado (al cliente)"

    evento = models.CharField(
        max_length=50,
        choices=Evento.choices,
        unique=True,
    )

    asunto = models.CharField(max_length=200)

    cuerpo = models.TextField()

    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plantilla de correo"
        verbose_name_plural = "Plantillas de correo"

    def __str__(self):
        return self.get_evento_display()

    @property
    def descripcion(self):
        return {
            "registro_cliente": "Se envía cuando un cliente se registra y recibe su ID.",
            "orden_creada_cliente": "Se envía al cliente cuando crea una orden directa o asistida.",
            "orden_creada_admin": "Se envía al administrador cuando un cliente crea una orden.",
            "estado_actualizado": "Se envía al cliente cuando pulsas «Notificar al cliente» en el panel (no se envía solo al cambiar el estado).",
        }.get(self.evento, "")


# ============================================================
# REGISTRO DE CORREOS ENVIADOS
# ============================================================

class RegistroCorreo(models.Model):

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Enviando"
        ENVIADO = "enviado", "Enviado"
        FALLIDO = "fallido", "No se envió"

    evento = models.CharField(max_length=50)

    destinatario = models.CharField(max_length=254)

    asunto = models.CharField(max_length=200)

    cuerpo = models.TextField()

    # Tracking ID de la orden o número de cliente, para ubicar el correo
    referencia = models.CharField(
        max_length=60,
        blank=True,
        default="",
    )

    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )

    error = models.TextField(blank=True, default="")

    intentos = models.PositiveSmallIntegerField(default=0)

    # Un fallo "resuelto" ya fue reenviado con éxito o descartado
    resuelto = models.BooleanField(default=False, db_index=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    fecha_envio = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_creacion"]
        verbose_name = "Registro de correo"
        verbose_name_plural = "Registro de correos"

    def __str__(self):
        return f"{self.get_estado_display()} - {self.destinatario} - {self.asunto}"

    @property
    def evento_legible(self):
        return dict(PlantillaCorreo.Evento.choices).get(self.evento, self.evento)
