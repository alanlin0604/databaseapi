# market_app/admin.py

from django.contrib import admin
from .models import (
    Member, Category, Stall, Product, CartItem, MemberAddress, 
    ParentOrder, SubOrder, OrderItem
)

# 註冊您的核心模型
admin.site.register(Member)
admin.site.register(Category)
admin.site.register(Stall)
admin.site.register(Product)
admin.site.register(CartItem)

# (可選) 註冊其他模型，以便在 Admin 介面操作
# admin.site.register(MemberAddress)
# admin.site.register(ParentOrder)
# admin.site.register(SubOrder)
# admin.site.register(OrderItem)