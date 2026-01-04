from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StallViewSet, ProductViewSet, CategoryViewSet, CartItemViewSet, home_page, cart_page

router = DefaultRouter()
router.register(r'stalls', StallViewSet, basename='stall')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'cart', CartItemViewSet, basename='cart')

urlpatterns = [
    path('api/', include(router.urls)),   
    path('', home_page, name='home'),   # 這裡是處理 127.0.0.1:8000/ 的地方
    path('cart/', cart_page, name='cart_page'),
]