# market_app/views.py (請將此內容寫入檔案)

from rest_framework import viewsets
from .models import Stall, Product, Category, CartItem
from .serializers import (
    StallSerializer, ProductSerializer, CategorySerializer, CartItemSerializer
)
# 注意：這裡的匯入必須與 serializers.py 中的定義完全一致！

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