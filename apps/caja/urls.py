from rest_framework.routers import DefaultRouter
from .views import AperturaViewSet, MovimientoCajaViewSet, CierreCajaViewSet

router = DefaultRouter()
router.register(r'aperturas', AperturaViewSet, basename='aperturas')
router.register(r'movimientos', MovimientoCajaViewSet, basename='movimientos-caja')
router.register(r'cierres', CierreCajaViewSet, basename='cierres')

urlpatterns = router.urls