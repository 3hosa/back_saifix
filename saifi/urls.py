from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def home(request):
    return HttpResponse("<h1>Welcome to Saifi Backend</h1><p>API is running.</p>")

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/core/', include('apps.authentication.urls')),
    path('api/wallets/', include('apps.wallets.urls')),
    path('api/financials/', include('apps.financials.urls')),
    path('api/recharge-payment/', include('apps.recharge_and_payment.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
