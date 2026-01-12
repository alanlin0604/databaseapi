from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os
import django

# 設定路徑
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('market_app.urls')), 
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# --- 自動初始化邏輯 (放在 urlpatterns 之後) ---
def init_cloud_data():
    # 只有在雲端環境 (有 DATABASE_URL) 才執行
    if os.environ.get('DATABASE_URL'):
        try:
            # 確保 Django App 已經完全載入
            django.setup()
            from market_app.models import Member, Category

            # 1. 自動建立管理員
            if not Member.objects.filter(username='admin').exists():
                Member.objects.create_superuser('admin', 'admin@example.com', 'password123')
                print("✅ 管理員帳號 admin/password123 建立成功")

            # 2. 自動建立一個分類 (否則首頁會因為撈不到 Category 而顯示忙碌)
            if not Category.objects.exists():
                Category.objects.create(name="一般商品", is_active=True)
                print("✅ 預設分類建立成功")
                
        except Exception as e:
            print(f"⚠️ 自動初始化跳過或失敗: {e}")

# 執行初始化
init_cloud_data()