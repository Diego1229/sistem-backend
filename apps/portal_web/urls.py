from django.urls import path
from .views import (
    CatalogoPublicoView,
    CategoriasPublicasView,
    SedesPublicasView,
    GenerarLinkWhatsAppView
)

urlpatterns = [
    path('catalogo/', CatalogoPublicoView.as_view(), name='catalogo-publico'),
    path('categorias/', CategoriasPublicasView.as_view(), name='categorias-publicas'),
    path('sedes/', SedesPublicasView.as_view(), name='sedes-publicas'),
    path('whatsapp/', GenerarLinkWhatsAppView.as_view(), name='generar-whatsapp'),
]