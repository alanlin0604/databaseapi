# online_market_site/urls.py (專案層級)

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 這裡將 '/api/' 路徑導向 market_app/urls.py
    path('api/', include('market_app.urls')), 
]