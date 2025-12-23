from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StallViewSet, ProductViewSet, CategoryViewSet, CartItemViewSet

# 使用 DefaultRouter 註冊 ViewSets
router = DefaultRouter()
router.register(r'stalls', StallViewSet, basename='stall')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'cart', CartItemViewSet, basename='cart')

# API 根路由
urlpatterns = [
    path('', include(router.urls)),
]