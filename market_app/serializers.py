# market_app/serializers.py (請將此內容寫入檔案)

from rest_framework import serializers
from .models import Stall, Product, Category, CartItem, Member
# 匯入所有相關模型，確保沒有匯入 'MemberPaymentToken' 等不存在的模型

# 序列化器定義
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class StallSerializer(serializers.ModelSerializer):
    # ✅ 移除手動定義的 owner_member 欄位！
    # 刪除這一行: owner_member = MemberSerializer(read_only=True) 
    
    class Meta:
        model = Stall
        fields = '__all__' 
        # 讓 ModelSerializer 自動處理 owner_member，它將生成一個 PrimaryKeyRelatedField (可寫入 ID)

# market_app/serializers.py (修正後的 ProductSerializer)

# ... (StallSerializer 等其他序列化器保持不變)

class ProductSerializer(serializers.ModelSerializer):
    # ✅ 刪除這一行！讓 ModelSerializer 自動處理 category 外鍵。
    # 刪除: category = CategorySerializer(read_only=True) 
    
    class Meta:
        model = Product
        fields = '__all__' 
        # 讓 ModelSerializer 自動生成 PrimaryKeyRelatedField (可寫入 ID)
        
# ... (CartItemSerializer 保持不變)

# market_app/serializers.py (修正後的 CartItemSerializer)

# ... (其他序列化器保持不變)

class CartItemSerializer(serializers.ModelSerializer):
    # ✅ 移除手動定義的 product 欄位！
    # 刪除: product = ProductSerializer(read_only=True) 
    
    class Meta:
        model = CartItem
        fields = '__all__'
        # ✅ 移除 'member'，讓它可以接受 POST 傳遞的 ID
        read_only_fields = ('added_at',)