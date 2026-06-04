from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaViewSet, ProductoViewSet,
    InventarioViewSet, MovimientoViewSet, LoteViewSet
)

router = DefaultRouter()
router.register(r'categorias', CategoriaViewSet, basename='categorias')
router.register(r'productos', ProductoViewSet, basename='productos')
router.register(r'inventario', InventarioViewSet, basename='inventario')
router.register(r'movimientos', MovimientoViewSet, basename='movimientos')
router.register(r'lotes', LoteViewSet, basename='lotes')

urlpatterns = router.urls