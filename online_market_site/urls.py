from django.contrib import admin
from django.urls import path, include
from market_app.models import Member
import os

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    # 這行是關鍵！它會把 market_app 裡所有的路由（包含首頁和 API）拉進來
    path('', include('market_app.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if os.environ.get('DATABASE_URL'):
    try:
        if not Member.objects.filter(username='admin').exists():
            Member.objects.create_superuser('admin', 'admin@example.com', 'password123')
            print("✅ 管理員帳號 admin/password123 建立成功")
    except:
        pass