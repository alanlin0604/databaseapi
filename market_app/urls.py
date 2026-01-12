# market_app/urls.py

from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from .views import (
    StallViewSet, ProductViewSet, CategoryViewSet, 
    CartItemViewSet, ParentOrderViewSet, OrderItemViewSet,
    StallProductManagerViewSet, MemberMeView, StallOrderManagerViewSet, # ✅ 匯入新視圖
    home_page, cart_page, payment_page, orders_page, RegisterView, CustomLoginView, login_page
)

# 建立 REST Framework 路由
router = DefaultRouter()
router.register(r'stalls', StallViewSet, basename='stall')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'cart', CartItemViewSet, basename='cart')
router.register(r'parent-orders', ParentOrderViewSet, basename='parentorder')
router.register(r'order-items', OrderItemViewSet, basename='orderitem')
router.register(r'stall-manager/orders', StallOrderManagerViewSet, basename='stall-order-manager')

# ✅ 註冊攤商管理專用的商品 API 路由
router.register(r'stall-manager/products', StallProductManagerViewSet, basename='stall-product-manager')

urlpatterns = [
    # API 路由
    path('api/', include(router.urls)),   
    path('api/register/', RegisterView.as_view(), name='api_register'),
    path('api/login/', CustomLoginView.as_view(), name='api_login'),
    path('api/member/me/', MemberMeView.as_view(), name='api_member_me'), # ✅ 會員點數與資訊 API

    # 前端頁面路由
    path('', home_page, name='home'),     
    path('cart/', cart_page, name='cart_page'),
    path('payment/', payment_page, name='payment_page'),
    path('my-orders/', orders_page, name='orders_page'),
    path('login/', login_page, name='login_page'),
    
    # ✅ 新增：攤商管理頁面路由
    path('stall-admin/', lambda r: render(r, 'stall_admin.html'), name='stall_admin_page'),
]