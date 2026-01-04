# market_app/views.py

from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication
from .models import Stall, Product, Category, CartItem
from .serializers import (
    StallSerializer, ProductSerializer, CategorySerializer, CartItemSerializer
)

# 1. 建立一個自定義的驗證類別來繞過 CSRF 檢查
class UnsafeSessionAuthentication(SessionAuthentication):
    def enforce_csrf(self, request):
        return  # 直接回傳，不執行任何 CSRF 檢查

def home_page(request):
    return render(request, 'index.html')

class StallViewSet(viewsets.ModelViewSet):
    queryset = Stall.objects.all()
    serializer_class = StallSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CartItemViewSet(viewsets.ModelViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    # 2. 指定這個 ViewSet 使用我們自定義的「不安全」驗證方式
    authentication_classes = [UnsafeSessionAuthentication]

def cart_page(request):
    return render(request, 'cart.html')