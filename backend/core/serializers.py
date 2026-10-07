from rest_framework import serializers

from .models import (
    Cliente,
    HistorialEstado,
    NotaOrden,
    Orden,
)


# ============================================================
# CLIENTE
# ============================================================

class ClienteSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cliente
        fields = [
            "id",
            "customer_number",
            "nombre",
            "apellidos",
            "telefono",
            "whatsapp",
            "email",
            "direccion",
            "ciudad",
            "provincia",
            "direccion_entrega",
            "instrucciones_entrega",
            "activo",
            "fecha_registro",
            "fecha_actualizacion",
        ]

        read_only_fields = [
            "id",
            "customer_number",
            "fecha_registro",
            "fecha_actualizacion",
        ]


# ============================================================
# HISTORIAL DE ESTADOS
# ============================================================

class HistorialEstadoSerializer(serializers.ModelSerializer):

    class Meta:
        model = HistorialEstado
        fields = [
            "id",
            "estado_anterior",
            "estado_nuevo",
            "nota",
            "usuario",
            "fecha",
            "orden",
        ]

        read_only_fields = [
            "id",
            "fecha",
        ]


# ============================================================
# NOTAS
# ============================================================

class NotaOrdenSerializer(serializers.ModelSerializer):

    class Meta:
        model = NotaOrden
        fields = [
            "id",
            "texto",
            "usuario",
            "fecha",
            "orden",
        ]

        read_only_fields = [
            "id",
            "fecha",
        ]


# ============================================================
# ORDEN
# ============================================================

class OrdenSerializer(serializers.ModelSerializer):

    cliente_customer_number = serializers.IntegerField(
        source="cliente.customer_number",
        read_only=True,
    )

    cliente_nombre = serializers.SerializerMethodField()

    historial = HistorialEstadoSerializer(
        many=True,
        read_only=True,
    )

    notas = NotaOrdenSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Orden

        fields = [
            "id",
            "historial",
            "notas",

            "cliente_customer_number",
            "cliente_nombre",

            "tracking_id",
            "tipo",
            "producto",
            "cantidad",
            "peso",
            "precio",
            "estado",

            "destinatario_nombre",
            "destinatario_telefono",
            "destinatario_direccion",

            "observaciones",
            "notas_internas",

            "fecha_creacion",
            "fecha_actualizacion",
        ]

        read_only_fields = [
            "id",
            "tracking_id",
            "estado",
            "cliente_customer_number",
            "cliente_nombre",
            "historial",
            "notas",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_cliente_nombre(self, obj):
        return f"{obj.cliente.nombre} {obj.cliente.apellidos}".strip()


# ============================================================
# CREACIÓN DE ORDEN
# ============================================================

class CrearOrdenSerializer(serializers.Serializer):

    customer_number = serializers.IntegerField(
        min_value=231
    )

    producto = serializers.CharField(
        max_length=255
    )

    cantidad = serializers.IntegerField(
        min_value=1,
        default=1
    )

    peso = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    tipo = serializers.ChoiceField(
        choices=Orden.TipoOrden.choices,
        default=Orden.TipoOrden.DIRECTA,
    )

    precio = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
        required=False,
        allow_null=True,
    )

    destinatario_nombre = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    destinatario_telefono = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )

    destinatario_direccion = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
    )


# ============================================================
# CAMBIO DE ESTADO
# ============================================================

class CambiarEstadoSerializer(serializers.Serializer):

    estado = serializers.ChoiceField(
        choices=Orden.Estado.choices
    )

    nota = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


# ============================================================
# CREAR NOTA
# ============================================================

class CrearNotaSerializer(serializers.Serializer):

    texto = serializers.CharField(
        min_length=1
    )