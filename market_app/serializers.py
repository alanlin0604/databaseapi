# market_app/serializers.py
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Stall, Product, Category, CartItem, Member, ParentOrder, SubOrder, OrderItem

# -----------------------------------------------------
# 會員資料序列化
# -----------------------------------------------------
class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Member
        fields = '__all__'

# -----------------------------------------------------
# 商品分類序列化
# -----------------------------------------------------
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

# -----------------------------------------------------
# 攤商資料序列化 (處理 Logo 圖片優先級)
# -----------------------------------------------------
class StallSerializer(serializers.ModelSerializer):
    # ✅ 增加一個 MethodField 來處理圖片顯示邏輯 (動態計算欄位)
    logo_display = serializers.SerializerMethodField()

    class Meta:
        model = Stall
        fields = [
            'id', 'name', 'description', 'contact_phone', 
            'logo_url', 'logo_image', 'logo_display', 
            'open_time', 'close_time', 'is_active'
        ]

    def get_logo_display(self, obj):
        """
        處理邏輯：優先回傳上傳的實體檔案路徑，若無則回傳手填的外部網址
        """
        if obj.logo_image and hasattr(obj.logo_image, 'url'):
            return obj.logo_image.url
        return obj.logo_url

# -----------------------------------------------------
# 商品資料序列化 (處理商品照片優先級)
# -----------------------------------------------------
class ProductSerializer(serializers.ModelSerializer):
    # 用於前端統一呼叫的圖片連結欄位
    image_display = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'stall', 'category', 'name', 'description', 
            'unit', 'price', 'stock_quantity', 'image', 
            'image_url', 'image_display', 'status'
        ]
        # stall 欄位由後端自動判斷，前端不可修改
        read_only_fields = ('stall',)

    def get_image_display(self, obj):
        # ✅ 安全檢查：確保實體檔案存在才呼叫 .url，避免檔案遺失時報 500 錯誤
        if obj.image and hasattr(obj.image, 'url'):
            return obj.image.url
        return obj.image_url

# -----------------------------------------------------
# 購物車項目序列化
# -----------------------------------------------------
class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = '__all__'
        # 會員與加入時間由後端自動處理
        read_only_fields = ('added_at', 'member')

# -----------------------------------------------------
# 子訂單序列化 (攤商端管理使用)
# -----------------------------------------------------
class SubOrderSerializer(serializers.ModelSerializer):
    # 透過 source 取得關聯表的特定文字欄位，方便前端顯示不需要再串接 API
    stall_name = serializers.ReadOnlyField(source='stall.name')
    parent_order_id = serializers.ReadOnlyField(source='parent_order.id')
    customer_name = serializers.ReadOnlyField(source='parent_order.member.username')
    
    class Meta:
        model = SubOrder
        fields = [
            'id', 'parent_order', 'parent_order_id', 'customer_name', 
            'stall', 'stall_name', 'delivery_type', 'order_status'
        ]

# -----------------------------------------------------
# 父訂單序列化 (顧客端查看完整訂單使用)
# -----------------------------------------------------
class ParentOrderSerializer(serializers.ModelSerializer):
    # 巢狀序列化：在父訂單中直接展開所有相關的子訂單資訊
    sub_orders = SubOrderSerializer(many=True, read_only=True)
    # ✅ 動態計算：該訂單預計獲得的點數回饋
    earned_points = serializers.SerializerMethodField()

    class Meta:
        model = ParentOrder
        fields = [
            'id', 'member', 'order_date', 
            'final_paid_amount', 'payment_method', 'order_status', 
            'sub_orders', 'earned_points' 
        ]

    def get_earned_points(self, obj):
        # 點數回饋邏輯：每消費 50 元回饋 1 點
        return int(obj.final_paid_amount // 50)

# -----------------------------------------------------
# 訂單明細序列化 (具體購買的商品內容)
# -----------------------------------------------------
class OrderItemSerializer(serializers.ModelSerializer):
    # 這裡的 product_name 是從 Snapshot 中或關聯 Product 取得
    product_name = serializers.ReadOnlyField(source='product.name')
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'sub_order', 'product', 'product_name', 
            'unit_price_snapshot', 'quantity'
        ]

# -----------------------------------------------------
# 註冊專用序列化器 (處理密碼雜湊與安全性)
# -----------------------------------------------------
class RegisterSerializer(serializers.ModelSerializer):
    # 密碼欄位設為 write_only，代表 API 回傳時不會包含密碼雜湊值
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Member
        fields = ('username', 'password', 'email')

    def create(self, validated_data):
        """
        覆寫 create 方法，使用 create_user 確保密碼經過正確的雜湊加密處理
        """
        return Member.objects.create_user(**validated_data)