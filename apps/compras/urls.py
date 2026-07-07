from rest_framework.routers import DefaultRouter
from .views import (
    ProveedorViewSet, CompraViewSet,
    FacturaAbastecimientoViewSet, DevolucionCompraViewSet
)

router = DefaultRouter()
router.register(r'proveedores', ProveedorViewSet, basename='proveedores')
router.register(r'ordenes', CompraViewSet, basename='ordenes')
router.register(r'facturas', FacturaAbastecimientoViewSet, basename='facturas-abastecimiento')
router.register(r'devoluciones', DevolucionCompraViewSet, basename='devoluciones-compra')

urlpatterns = router.urls