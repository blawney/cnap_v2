from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, re_path, include

from rest_framework.authtoken import views as authtoken_views

from . import views as base_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include('custom_auth.user_urls')),
    path('resources/', include('base.resource_urls')),
    path('organizations/', include('base.organization_urls')),
    path('auth/', include('custom_auth.urls')),
    path('analysis/', include('analysis.urls')),
    re_path(r'^api/$', base_views.api_root),
    re_path(r'^api-auth/', include('rest_framework.urls')),
    re_path(r'^api-token-auth/', authtoken_views.obtain_auth_token),
    path(r'transfers/', include('transfer_app.urls')),
    path(r'dashboard/', include('dashboard.urls')),
    re_path(r'^$', base_views.index),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
