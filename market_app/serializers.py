# market_app/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Stall, Product, Category, CartItem, Member, ParentOrder, SubOrder, OrderItem

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class StallSerializer(serializers.ModelSerializer):
    # ✅ 增加一個 MethodField 來處理圖片顯示邏輯
    logo_display = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = ['id', 'name', 'description', 'contact_phone', 'logo_url', 'logo_image', 'logo_display', 'open_time', 'close_time', 'is_active']

    def get_logo_display(self, obj):
        # 優先回傳上傳的實體檔案路徑，若無則回傳手填的網址
        if obj.logo_image and hasattr(obj.logo_image, 'url'):
            return obj.logo_image.url
        return obj.logo_url

class ProductSerializer(serializers.ModelSerializer):
    image_display = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'stall', 'category', 'name', 'description', 'unit', 'price', 'stock_quantity', 'image', 'image_url', 'image_display', 'status']
        read_only_fields = ('stall',)

    def get_image_display(self, obj):
        # ✅ 安全檢查：確保檔案存在才呼叫 .url，避免 500 錯誤
        if obj.image and hasattr(obj.image, 'url'):
            return obj.image.url
        return obj.image_url

class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'
        read_only_fields = ('added_at', 'member')

# ✅ 子訂單序列化器：加入 stall_name 方便前端顯示
class SubOrderSerializer(serializers.ModelSerializer):
    stall_name = serializers.ReadOnlyField(source='stall.name')
    # ✅ 新增：取得父訂單編號與顧客名稱
    parent_order_id = serializers.ReadOnlyField(source='parent_order.id')
    customer_name = serializers.ReadOnlyField(source='parent_order.member.username')
    
    class Meta:
        model = SubOrder
        fields = ['id', 'parent_order', 'parent_order_id', 'customer_name', 'stall', 'stall_name', 'delivery_type', 'order_status']

# ✅ 父訂單序列化器：修正 Redundant 報錯
class ParentOrderSerializer(serializers.ModelSerializer):
    sub_orders = SubOrderSerializer(many=True, read_only=True)
    # ✅ 新增：計算該訂單可獲得的點數
    earned_points = serializers.SerializerMethodField()

    class Meta:
        model = ParentOrder
        fields = [
            'id', 'member', 'order_date', 
            'final_paid_amount', 'payment_method', 'order_status', 'sub_orders',
            'earned_points' 
        ]

    def get_earned_points(self, obj):
        # 回傳每50元一點的整數結果
        return int(obj.final_paid_amount // 50)

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source='product.name')
    class Meta:
        model = OrderItem
        fields = ['id', 'sub_order', 'product', 'product_name', 'unit_price_snapshot', 'quantity']

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = Member
        fields = ('username', 'password', 'email')
    def create(self, validated_data):
        return Member.objects.create_user(**validated_data)