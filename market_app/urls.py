# market_app/urls.py

from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from .views import (
    StallViewSet, ProductViewSet, CategoryViewSet, 
    CartItemViewSet, ParentOrderViewSet, OrderItemViewSet,
    StallProductManagerViewSet, MemberMeView, StallOrderManagerViewSet, # ✅ 匯入管理端專用視圖
    home_page, cart_page, payment_page, orders_page, RegisterView, CustomLoginView, login_page
)

# -----------------------------------------------------
# 1. REST Framework 自動路由設定 (ViewSets)
# -----------------------------------------------------
# 使用 DefaultRouter 可以自動產生 CRUD 的 URL 模式（如 GET/POST/PATCH/DELETE）
router = DefaultRouter()

# 顧客端常用路由
router.register(r'stalls', StallViewSet, basename='stall')           # 攤商列表與詳情
router.register(r'products', ProductViewSet, basename='product')     # 商品列表與詳情
router.register(r'categories', CategoryViewSet, basename='category') # 商品分類介面
router.register(r'cart', CartItemViewSet, basename='cart')           # 購物車增刪改查與結帳

# 訂單相關路由
router.register(r'parent-orders', ParentOrderViewSet, basename='parentorder') # 顧客查看總訂單
router.register(r'order-items', OrderItemViewSet, basename='orderitem')      # 訂單內的商品明細

# ✅ 攤商管理專用路由 (由管理員權限存取)
router.register(r'stall-manager/orders', StallOrderManagerViewSet, basename='stall-order-manager')   # 管理自家的子訂單
router.register(r'stall-manager/products', StallProductManagerViewSet, basename='stall-product-manager') # 管理自家的商品庫存

# -----------------------------------------------------
# 2. 總體路徑配置 (URL Patterns)
# -----------------------------------------------------
urlpatterns = [
    # --- API 數據介面 (供前端 Fetch 使用) ---
    path('api/', include(router.urls)),                      # 包含上方所有 router 註冊的 API
    path('api/register/', RegisterView.as_view(), name='api_register'), # 會員註冊接口
    path('api/login/', CustomLoginView.as_view(), name='api_login'),      # 會員登入與 Token 核發
    path('api/member/me/', MemberMeView.as_view(), name='api_member_me'), # 取得目前登入者的點數與基本資料

    # --- 前端頁面視圖 (回傳 HTML 範本) ---
    path('', home_page, name='home'),                      # 商城首頁
    path('cart/', cart_page, name='cart_page'),            # 購物車清單頁
    path('payment/', payment_page, name='payment_page'),   # 付款確認頁 (需帶 ?id=)
    path('my-orders/', orders_page, name='orders_page'),   # 會員購買紀錄頁
    path('login/', login_page, name='login_page'),         # 登入/註冊 切換頁
    
    # ✅ 攤商管理後台 (前端使用 lambda 直接渲染範本，邏輯由後端 API 驅動)
    path('stall-admin/', lambda r: render(r, 'stall_admin.html'), name='stall_admin_page'),
]