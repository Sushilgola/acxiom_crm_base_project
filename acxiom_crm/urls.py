from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='root'),
    path('auth/', include('core.urls')),
    path('', include('crm.urls')),
    path('reports/', include('reports.urls')),
    path('api/', include('api.urls')),
]
