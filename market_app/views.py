from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db.models import Sum, F
from django.db import transaction # ✅ 引入事務處理，確保庫存扣除安全
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

# --- 頁面路由 ---
def home_page(request): return render(request, 'index.html')
def cart_page(request): return render(request, 'cart.html')
def payment_page(request): return render(request, 'payment.html')
def orders_page(request): return render(request, 'orders.html')
def login_page(request): return render(request, 'login.html')

# --- 會員認證與資訊 API ---

@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    """註冊新會員 (Member 即 User)"""
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
    serializer_class = ParentOrderSerializer
    authentication_classes = [TokenAuthentication] 
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ParentOrder.objects.filter(member=self.request.user).prefetch_related('sub_orders__stall').order_by('-id')

    # ✅ 新增：處理訂單付款後的自動集點邏輯
    def perform_update(self, serializer):
        # 取得更新前的原始狀態
        old_status = serializer.instance.order_status
        # 執行更新儲存
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
    """登入並取得 Token"""
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
    """包含儀表板數據統計的攤商 API"""
    serializer_class = StallSerializer
    authentication_classes = [TokenAuthentication]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    def get_queryset(self):
        # 區分前台與後台請求
        is_admin = self.request.query_params.get('admin', 'false') == 'true'
        if self.request.user.is_authenticated and is_admin:
            return Stall.objects.filter(owner_member=self.request.user)
        return Stall.objects.filter(is_active=True)

    def perform_create(self, serializer):
        serializer.save(owner_member=self.request.user)

    # ✅ 功能 1：攤商營收報表數據
    @action(detail=True, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def dashboard_stats(self, request, pk=None):
        stall = self.get_object()
        
        # 1. 修正：明確限定必須是父訂單已付款 (paid) 的訂單才計入營收
        # 2. 同時排除已取消的子訂單
        active_subs = SubOrder.objects.filter(
            stall=stall,
            parent_order__order_status='paid', # 確保真的收到錢了
            order_status__in=['received', 'preparing', 'ready_for_pickup', 'completed']
        )
        
        # 累計總營收 (不分日期)
        total_revenue = OrderItem.objects.filter(sub_order__in=active_subs).aggregate(
            total=Sum(F('unit_price_snapshot') * F('quantity'))
        )['total'] or 0

        # 今日營收：使用 localtime 確保與台灣/本地時間同步
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        today_revenue = OrderItem.objects.filter(
            sub_order__in=active_subs,
            sub_order__parent_order__order_date__gte=today_start # 大於等於今天凌晨
        ).aggregate(total=Sum(F('unit_price_snapshot') * F('quantity')))['total'] or 0

        # 熱銷排行
        top_products = OrderItem.objects.filter(sub_order__stall=stall, sub_order__parent_order__order_status='paid').values('product__name').annotate(
            total_qty=Sum('quantity')
        ).order_by('-total_qty')[:5]

        return Response({
            "today_revenue": today_revenue,
            "total_revenue": total_revenue,
            "top_products": top_products
        })

class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    def get_queryset(self):
        now_time = timezone.localtime().time()
        queryset = Product.objects.filter(
            status='on_shelf',
            stall__is_active=True,
            stall__open_time__lte=now_time,
            stall__close_time__gte=now_time
        ).select_related('stall')
        
        category_id = self.request.query_params.get('category')
        if category_id: queryset = queryset.filter(category_id=category_id)
        search_query = self.request.query_params.get('search')
        if search_query: queryset = queryset.filter(name__icontains=search_query)
        stall_id = self.request.query_params.get('stall')
        if stall_id: queryset = queryset.filter(stall_id=stall_id)
        return queryset

class StallProductManagerViewSet(viewsets.ModelViewSet):
    """攤商後台專用的商品管理 API"""
    serializer_class = ProductSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ✅ 只允許查看自己名下攤商的商品
        return Product.objects.filter(stall__owner_member=self.request.user)

    def perform_create(self, serializer):
        # ✅ 自動找出該會員擁有的攤商，解決 "stall 必填" 報錯
        stall = Stall.objects.filter(owner_member=self.request.user).first()
        if not stall:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"detail": "您尚未擁有任何攤商，無法新增商品。"})
        serializer.save(stall=stall)

    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        product = self.get_object()
        new_status = 'off_shelf' if product.status == 'on_shelf' else 'on_shelf'
        product.status = new_status
        product.save()
        return Response({'id': product.id, 'new_status': product.status})

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class StallOrderManagerViewSet(viewsets.ReadOnlyModelViewSet):
    """攤商訂單管理 API"""
    serializer_class = SubOrderSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SubOrder.objects.filter(stall__owner_member=self.request.user).order_by('-id')

    # ✅ 修正：改為接受 status 參數，不再寫死
    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        sub_order = self.get_object()
        new_status = request.data.get('status')
        
        # 定義允許的狀態，避免資料錯誤
        allowed_status = ['received', 'ready_for_pickup', 'completed', 'cancelled']
        
        if new_status in allowed_status:
            sub_order.order_status = new_status
            sub_order.save()
            return Response({'status': sub_order.order_status})
        
        return Response({'detail': '不支援的狀態值'}, status=400)
class OrderItemViewSet(viewsets.ReadOnlyModelViewSet):
    """支援按子訂單 ID 過濾的商品明細 API"""
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        parent_id = self.request.query_params.get('parent_id')
        sub_order_id = self.request.query_params.get('sub_order_id') # ✅ 增加支援
        queryset = OrderItem.objects.all()
        
        if parent_id:
            queryset = queryset.filter(sub_order__parent_order_id=parent_id)
        if sub_order_id:
            queryset = queryset.filter(sub_order_id=sub_order_id) # ✅ 讓攤商精確抓取該筆訂單品項
            
        return queryset

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(member=self.request.user).select_related('product')

    def create(self, request, *args, **kwargs):
        """覆寫建立邏輯：若商品已在購物車中，則自動累加數量，避免資料庫 Duplicate 錯誤"""
        member = request.user
        product_id = request.data.get('product')
        quantity = int(request.data.get('quantity', 1))

        # 🔍 檢查是否已經存在相同的商品記錄
        cart_item = CartItem.objects.filter(member=member, product_id=product_id).first()

        if cart_item:
            # 🔄 若存在：執行累加更新
            cart_item.quantity += quantity
            cart_item.save()
            serializer = self.get_serializer(cart_item)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        # 🆕 若不存在：執行原始建立邏輯
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(member=self.request.user)

    @action(detail=False, methods=['post'])
    def checkout(self, request):
        member = request.user
        try: use_points = int(request.data.get('use_points', 0))
        except: use_points = 0
        
        if use_points > member.current_points:
            return Response({"detail": "點數不足"}, status=400)

        with transaction.atomic():
            cart_items = CartItem.objects.select_for_update().filter(member=member)
            if not cart_items.exists(): return Response({"detail": "購物車是空的"}, status=400)

            total_amount = 0
            for item in cart_items:
                if item.product.stock_quantity < item.quantity:
                    return Response({"detail": f"商品 {item.product.name} 庫存不足"}, status=400)
                item.product.stock_quantity -= item.quantity
                item.product.save()
                total_amount += item.product.price * item.quantity

            final_amount = max(0, total_amount - use_points)
            parent_order = ParentOrder.objects.create(member=member, final_paid_amount=final_amount, payment_method='CASH', order_status='pending')
            if use_points > 0:
                member.current_points -= use_points
                member.save()

            stall_groups = {}
            for item in cart_items:
                sid = item.product.stall.id
                if sid not in stall_groups: stall_groups[sid] = []
                stall_groups[sid].append(item)

            for sid, items in stall_groups.items():
                sub = SubOrder.objects.create(parent_order=parent_order, stall_id=sid)
                for it in items:
                    OrderItem.objects.create(sub_order=sub, product=it.product, unit_price_snapshot=it.product.price, quantity=it.quantity)

            cart_items.delete()
            return Response({"order_id": parent_order.id, "final_amount": final_amount})