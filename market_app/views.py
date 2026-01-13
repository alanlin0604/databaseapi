from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Sum, F
from django.db import transaction # ✅ 引入事務處理，確保庫存扣除安全，避免超賣
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Stall, Product, Category, CartItem, ParentOrder, SubOrder, OrderItem, Member
from .serializers import (
    StallSerializer, ProductSerializer, CategorySerializer, 
    CartItemSerializer, ParentOrderSerializer, 
    OrderItemSerializer, RegisterSerializer, SubOrderSerializer
)

# --- 頁面路由：負責將 Django 網址導向正確的 HTML 範本 ---
def home_page(request): return render(request, 'index.html')
def cart_page(request): return render(request, 'cart.html')
def payment_page(request): return render(request, 'payment.html')
def orders_page(request): return render(request, 'orders.html')
def login_page(request): return render(request, 'login.html')

# --- 會員認證與資訊 API ---

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """
    註冊新會員：接收帳號密碼，建立 User 同時核發認證 Token
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = [] 

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            member = serializer.save() 
            token, created = Token.objects.get_or_create(user=member)
            return Response({
                "token": token.key, 
                "username": member.username,
                "detail": "註冊成功"
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ParentOrderViewSet(viewsets.ModelViewSet):
    """
    父訂單 ViewSet：處理顧客查看歷史訂單以及付款後的點數回饋
    """
    serializer_class = ParentOrderSerializer
    authentication_classes = [TokenAuthentication] 
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 僅回傳屬於登入者自己的訂單，並預先載入相關資料以優化效能
        return ParentOrder.objects.filter(member=self.request.user).prefetch_related('sub_orders__stall').order_by('-id')

    # ✅ Hook：處理訂單付款後的自動集點邏輯
    def perform_update(self, serializer):
        # 取得更新前的原始狀態 (確認是否原本是 pending)
        old_status = serializer.instance.order_status
        # 執行更新儲存 (變更狀態為 paid)
        instance = serializer.save()
        # 取得更新後的狀態
        new_status = instance.order_status

        # 判斷邏輯：如果訂單狀態從「非已付款」變更為「已付款(paid)」
        if old_status != 'paid' and new_status == 'paid':
            # 計算應得點數：每 50 元累積 1 點 (以最終支付金額為準)
            earned_points = int(instance.final_paid_amount // 50)
            
            if earned_points > 0:
                member = instance.member
                member.current_points += earned_points
                member.save()

@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(ObtainAuthToken):
    """
    登入並取得 Token：驗證帳密後回傳 API 呼叫所需的身份憑證
    """
    authentication_classes = [] 

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'username': user.username,
            'user_id': user.pk
        })

class MemberMeView(APIView):
    """
    個人資訊 API：回傳當前登入者的用戶名、餘額點數等
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request):
        return Response({
            "username": request.user.username,
            "current_points": request.user.current_points,
            "email": request.user.email
        })

# --- 功能 ViewSets ---

class StallViewSet(viewsets.ModelViewSet):
    """
    攤商 API：負責首頁攤商列表顯示以及管理端儀表板數據統計
    """
    serializer_class = StallSerializer
    authentication_classes = [TokenAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        # 區分請求對象：admin=true 代表管理後台，否則為前台首頁
        is_admin = self.request.query_params.get('admin', 'false') == 'true'
        if self.request.user.is_authenticated and is_admin:
            return Stall.objects.filter(owner_member=self.request.user)
        return Stall.objects.filter(is_active=True)

    def perform_create(self, serializer):
        # 建立攤商時，自動將當前使用者設定為攤主
        serializer.save(owner_member=self.request.user)

    # ✅ 擴充功能：攤商後台數據統計 (儀表板)
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def dashboard_stats(self, request, pk=None):
        stall = self.get_object()
        
        # 篩選有效子訂單：必須是母訂單已付款，且子訂單未取消
        active_subs = SubOrder.objects.filter(
            stall=stall,
            parent_order__order_status='paid', 
            order_status__in=['received', 'preparing', 'ready_for_pickup', 'completed']
        )
        
        # 累計總營收 (利用價格快照與數量計算)
        total_revenue = OrderItem.objects.filter(sub_order__in=active_subs).aggregate(
            total=Sum(F('unit_price_snapshot') * F('quantity'))
        )['total'] or 0

        # 今日營收：計算從今日凌晨 00:00 起算至今的營收
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = OrderItem.objects.filter(
            sub_order__in=active_subs,
            sub_order__parent_order__order_date__gte=today_start 
        ).aggregate(total=Sum(F('unit_price_snapshot') * F('quantity')))['total'] or 0

        # 熱銷排行前 5 名
        top_products = OrderItem.objects.filter(sub_order__stall=stall, sub_order__parent_order__order_status='paid').values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]

        return Response({
            "today_revenue": today_revenue,
            "total_revenue": total_revenue,
            "top_products": top_products
        })

class ProductViewSet(viewsets.ModelViewSet):
    """
    顧客端商品列表：自動過濾「營業中」攤商的商品，並支援分類與關鍵字搜尋
    """
    serializer_class = ProductSerializer
    def get_queryset(self):
        now_time = timezone.localtime().time()
        # 篩選條件：上架中 + 攤商營業中 + 符合目前當下營業時間
        queryset = Product.objects.filter(
            status='on_shelf',
            stall__is_active=True,
            stall__open_time__lte=now_time,
            stall__close_time__gte=now_time
        ).select_related('stall')
        
        # 處理分類過濾、搜尋關鍵字、特定攤商篩選
        category_id = self.request.query_params.get('category')
        if category_id: queryset = queryset.filter(category_id=category_id)
        search_query = self.request.query_params.get('search')
        if search_query: queryset = queryset.filter(name__icontains=search_query)
        stall_id = self.request.query_params.get('stall')
        if stall_id: queryset = queryset.filter(stall_id=stall_id)
        return queryset

class StallProductManagerViewSet(viewsets.ModelViewSet):
    """
    攤商後台商品管理：限定攤主本人操作，支援庫存修改與上下架
    """
    serializer_class = ProductSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 僅允許存取自己名下的商品
        return Product.objects.filter(stall__owner_member=self.request.user)

    def perform_create(self, serializer):
        # 新增商品時，自動綁定到攤主擁有的攤商
        stall = Stall.objects.filter(owner_member=self.request.user).first()
        if not stall:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "您尚未擁有任何攤商，無法新增商品。"})
        serializer.save(stall=stall)

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """一鍵上下架商品"""
        product = self.get_object()
        new_status = 'off_shelf' if product.status == 'on_shelf' else 'on_shelf'
        product.status = new_status
        product.save()
        return Response({'id': product.id, 'new_status': product.status})

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class StallOrderManagerViewSet(viewsets.ReadOnlyModelViewSet):
    """
    攤商後台訂單管理：僅回傳該攤商收到的子訂單，並提供狀態更新功能
    """
    serializer_class = SubOrderSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubOrder.objects.filter(stall__owner_member=self.request.user).order_by('-id')

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """更新出貨/備貨狀態 (如：備貨中 -> 可取貨)"""
        sub_order = self.get_object()
        new_status = request.data.get('status')
        allowed_status = ['received', 'ready_for_pickup', 'completed', 'cancelled']
        
        if new_status in allowed_status:
            sub_order.order_status = new_status
            sub_order.save()
            return Response({'status': sub_order.order_status})
        return Response({'detail': '不支援的狀態值'}, status=400)

class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """
    訂單項目 API：支援透過網址參數過濾特定母訂單或子訂單的所有商品
    """
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent_id')
        sub_order_id = self.request.query_params.get('sub_order_id')
        queryset = OrderItem.objects.all()
        
        if parent_id:
            queryset = queryset.filter(sub_order__parent_order_id=parent_id)
        if sub_order_id:
            queryset = queryset.filter(sub_order_id=sub_order_id)
        return queryset

class CartItemViewSet(viewsets.ModelViewSet):
    """
    購物車核心系統：處理加入購物車邏輯與「結帳事務處理」
    """
    serializer_class = CartItemSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(member=self.request.user).select_related('product')

    def create(self, request, *args, **kwargs):
        """
        優化：加入購物車時，若商品已存在，則更新數量而非新增記錄
        """
        member = request.user
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))

        cart_item = CartItem.objects.filter(member=member, product_id=product_id).first()
        if cart_item:
            cart_item.quantity += quantity
            cart_item.save()
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(member=self.request.user)

    # ✅ 關鍵邏輯：購物車結帳
    @action(detail=False, methods=['post'])
    def checkout(self, request):
        """
        將購物車轉為訂單，涉及點數抵扣、庫存扣除、跨攤商子訂單拆分
        """
        member = request.user
        try: use_points = int(request.data.get('use_points', 0))
        except: use_points = 0
        
        # 1. 檢查會員點數是否足夠
        if use_points > member.current_points:
            return Response({"detail": "點數不足"}, status=400)

        # 2. 開啟資料庫事務處理，確保結帳過程發生錯誤時會全數回滾，避免庫存錯亂
        with transaction.atomic():
            # 使用 select_for_update() 鎖定記錄，防止高並發下的庫存競爭
            cart_items = CartItem.objects.select_for_update().filter(member=member)
            if not cart_items.exists(): return Response({"detail": "購物車是空的"}, status=400)

            # 3. 庫存檢查與初步扣除
            total_amount = 0
            for item in cart_items:
                if item.product.stock_quantity < item.quantity:
                    return Response({"detail": f"商品 {item.product.name} 庫存不足"}, status=400)
                item.product.stock_quantity -= item.quantity
                item.product.save()
                total_amount += item.product.price * item.quantity

            # 4. 計算折抵後金額並建立父訂單
            final_amount = max(0, total_amount - use_points)
            parent_order = ParentOrder.objects.create(
                member=member, 
                final_paid_amount=final_amount, 
                payment_method='CASH', 
                order_status='pending'
            )
            
            # 5. 扣除點數
            if use_points > 0:
                member.current_points -= use_points
                member.save()

            # 6. 按攤商拆分子訂單 (子訂單架構讓各攤商能各自管理訂單)
            stall_groups = {}
            for item in cart_items:
                sid = item.product.stall.id
                if sid not in stall_groups: stall_groups[sid] = []
                stall_groups[sid].append(item)

            for sid, items in stall_groups.items():
                sub = SubOrder.objects.create(parent_order=parent_order, stall_id=sid)
                for it in items:
                    # 儲存單價快照，避免未來商品價格變動影響已成立訂單
                    OrderItem.objects.create(
                        sub_order=sub, 
                        product=it.product, 
                        unit_price_snapshot=it.product.price, 
                        quantity=it.quantity
                    )

            # 7. 清空購物車，事務完成
            cart_items.delete()
            return Response({"order_id": parent_order.id, "final_amount": final_amount})