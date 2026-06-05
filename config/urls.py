
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/configuracion/', include('apps.configuracion.urls')),
    path('api/v1/usuarios/', include('apps.usuarios.urls')),
    path('api/v1/inventario/', include('apps.inventario.urls')),
    path('api/v1/compras/', include('apps.compras.urls')),
    path('api/v1/caja/', include('apps.caja.urls')),
    path('api/v1/ventas/', include('apps.ventas.urls')),

    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
