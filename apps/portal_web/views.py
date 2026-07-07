from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import generics

from apps.inventario.models import Producto, Inventario, Categoria
from apps.configuracion.models import Sede
from apps.inventario.serializers import ProductoListSerializer, CategoriaSerializer
from apps.configuracion.serializers import SedeSerializer


class CatalogoPublicoView(generics.ListAPIView):
    """
    GET /api/v1/web/catalogo/
    Catálogo público de productos activos con stock disponible.
    No requiere autenticación — es la vista de la landing page.
    """
    permission_classes = [AllowAny]
    serializer_class = ProductoListSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ['nombre', 'descripcion']

    def get_queryset(self):
        qs = Producto.objects.filter(
            activo=True
        ).select_related('impuesto').prefetch_related(
            'categorias__categoria'
        )

        # Filtrar por categoría si se pasa como query param
        categoria_id = self.request.query_params.get('categoria')
        if categoria_id:
            qs = qs.filter(categorias__categoria_id=categoria_id)

        # Filtrar por sede si se pasa — muestra solo productos con stock
        sede_id = self.request.query_params.get('sede')
        if sede_id:
            qs = qs.filter(
                stocks__sede_id=sede_id,
                stocks__cantidad__gt=0
            )

        return qs.distinct()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'ok': True,
            'data': serializer.data,
            'total': queryset.count()
        })


class CategoriasPublicasView(generics.ListAPIView):
    """
    GET /api/v1/web/categorias/
    Lista de categorías activas para el menú del catálogo.
    No requiere autenticación.
    """
    permission_classes = [AllowAny]
    serializer_class = CategoriaSerializer

    def get_queryset(self):
        return Categoria.objects.filter(activo=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'ok': True, 'data': serializer.data})


class SedesPublicasView(generics.ListAPIView):
    """
    GET /api/v1/web/sedes/
    Lista de sedes activas con su WhatsApp para el botón de pedido.
    No requiere autenticación.
    """
    permission_classes = [AllowAny]
    serializer_class = SedeSerializer

    def get_queryset(self):
        return Sede.objects.filter(activo=True)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'ok': True, 'data': serializer.data})


class GenerarLinkWhatsAppView(APIView):
    """
    POST /api/v1/web/whatsapp/
    Genera el link de WhatsApp con el mensaje pre-armado de los productos.
    El frontend llama esto con la lista de productos del carrito local
    y recibe el link listo para abrir wa.me

    No requiere autenticación.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        sede_id = request.data.get('sede_id')
        items = request.data.get('items', [])

        if not sede_id:
            return Response({
                'ok': False,
                'error': 'SEDE_REQUERIDA',
                'message': 'Debe especificar la sede.'
            }, status=400)

        try:
            sede = Sede.objects.get(pk=sede_id, activo=True)
        except Sede.DoesNotExist:
            return Response({
                'ok': False,
                'error': 'SEDE_NO_ENCONTRADA',
                'message': 'Sede no encontrada.'
            }, status=404)

        if not sede.whatsapp:
            return Response({
                'ok': False,
                'error': 'SIN_WHATSAPP',
                'message': 'Esta sede no tiene WhatsApp configurado.'
            }, status=400)

        # Armar el texto de productos
        lineas = []
        for item in items:
            nombre = item.get('nombre', 'Producto')
            cantidad = item.get('cantidad', 1)
            precio = item.get('precio', 0)
            lineas.append(f"• {nombre} x{cantidad} — ${precio:,.0f}")

        productos_texto = '\n'.join(lineas) if lineas else 'Sin productos'

        # Usar plantilla de la sede o mensaje genérico
        plantilla = sede.whatsapp_mensaje_plantilla or \
            'Hola, me gustaría hacer el siguiente pedido:\n{productos}'

        mensaje = plantilla.replace('{productos}', productos_texto)

        # Generar link wa.me
        import urllib.parse
        numero = sede.whatsapp.replace('+', '').replace(' ', '')
        link = f"https://wa.me/{numero}?text={urllib.parse.quote(mensaje)}"

        return Response({
            'ok': True,
            'data': {
                'link': link,
                'numero': sede.whatsapp,
                'mensaje': mensaje
            },
            'message': 'Link generado correctamente.'
        })