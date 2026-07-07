from rest_framework.routers import DefaultRouter
from .views import ClienteViewSet, VentaViewSet, DevolucionVentaViewSet

router = DefaultRouter()
router.register(r'clientes', ClienteViewSet, basename='clientes')
router.register(r'devoluciones', DevolucionVentaViewSet, basename='devoluciones-venta')
router.register(r'', VentaViewSet, basename='ventas')

urlpatterns = router.urls