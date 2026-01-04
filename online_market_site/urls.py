from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # 這行是關鍵！它會把 market_app 裡所有的路由（包含首頁和 API）拉進來
    path('', include('market_app.urls')), 
]