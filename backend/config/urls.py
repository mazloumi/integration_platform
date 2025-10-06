from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf.urls.static import static
from django.conf import settings
from integrations.models import IntegrationConfiguration, IntegrationRun

from integrations.views import (
    IntegrationConfigurationViewSet,
    IntegrationRunViewSet,
    webhook_handler,
    pubsub_push_handler,
    mapper_view
)

router = DefaultRouter()
router.register(r'integrations', IntegrationConfigurationViewSet, basename='integration')
router.register(r'runs', IntegrationRunViewSet, basename='integration-run')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('webhook/<str:webhook_path>/', webhook_handler, name='webhook-handler'),
    path('pubsub/<str:push_path>/', pubsub_push_handler, name='pubsub-push-handler'),
    path('mapper/', mapper_view, name='mapper'),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)