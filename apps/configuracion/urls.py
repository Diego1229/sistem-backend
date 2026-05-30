from rest_framework.routers import DefaultRouter
from .views import (
    SedeViewSet, MetodoPagoViewSet, TipoMovimientoInvViewSet,
    TipoMovimientoCajaViewSet, ImpuestoViewSet, CajaViewSet, ConsecutivoViewSet
)

router = DefaultRouter()
router.register(r'sedes', SedeViewSet, basename='sedes')
router.register(r'metodos-pago', MetodoPagoViewSet, basename='metodos-pago')
router.register(r'tipos-movimiento-inv', TipoMovimientoInvViewSet, basename='tipos-mov-inv')
router.register(r'tipos-movimiento-caja', TipoMovimientoCajaViewSet, basename='tipos-mov-caja')
router.register(r'impuestos', ImpuestoViewSet, basename='impuestos')
router.register(r'cajas', CajaViewSet, basename='cajas')
router.register(r'consecutivos', ConsecutivoViewSet, basename='consecutivos')

urlpatterns = router.urls