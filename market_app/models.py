from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

# -----------------------------------------------------
# 狀態與選項定義 (保留所有原有定義)
# -----------------------------------------------------
STATUS_CHOICES = [
    ('active', _('活躍中')),
    ('inactive', _('未啟用')),
    ('banned', _('已禁用')),
]

APPROVAL_STATUS_CHOICES = [
    ('pending', _('待審核')),
    ('approved', _('已批准')),
    ('rejected', _('已拒絕')),
]

PRODUCT_STATUS_CHOICES = [
    ('on_shelf', _('上架中')),
    ('off_shelf', _('已下架')),
    ('draft', _('草稿')),
]

PAYMENT_METHOD_CHOICES = [
    ('CASH', _('現場現金')),
    ('LINE_PAY', _('LINE Pay')),
    ('ALL_PAY', _('全支付')),
]

DELIVERY_TYPE_CHOICES = [
    ('PICKUP', _('到攤取貨')),
    ('DELIVERY', _('宅配')),
]

ORDER_STATUS_CHOICES = [
    ('pending', _('待付款')),
    ('paid', _('已付款')),
    ('cancelled', _('已取消')),
    ('completed', _('已完成')),
    ('ready_for_pickup', _('可取貨')),
]

SUB_ORDER_STATUS_CHOICES = [
    ('received', _('已接單')),
    ('preparing', _('備貨中')),
    ('ready_for_pickup', _('可取貨')),
    ('shipped', _('已出貨')),
    ('completed', _('已完成')),
    ('cancelled', _('已取消')),
]

# -----------------------------------------------------
# 1. 平台通用類別表
# -----------------------------------------------------
class Category(models.Model):
    name = models.CharField(_('類別名稱'), max_length=100, unique=True)
    is_active = models.BooleanField(_('是否啟用'), default=True)
    created_at = models.DateTimeField(_('建立時間'), auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name = _('商品分類')
        verbose_name_plural = _('商品分類')

    def __str__(self):
        return self.name

# -----------------------------------------------------
# 2. 會員資訊表
# -----------------------------------------------------
class Member(AbstractUser):
    phone = models.CharField(_('聯絡電話'), max_length=20, unique=True, null=True, blank=True)
    current_points = models.PositiveIntegerField(_('目前點數餘額'), default=0)
    status = models.CharField(_('帳號狀態'), max_length=10, choices=STATUS_CHOICES, default='active')

    class Meta:
        db_table = 'members'
        verbose_name = _('會員')
        verbose_name_plural = _('會員')

    def __str__(self):
        return self.username

# -----------------------------------------------------
# 3. 攤商資訊表 (新增：營業時間)
# -----------------------------------------------------
class Stall(models.Model):
    owner_member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=_('攤商管理者'), related_name='owned_stalls')
    name = models.CharField(_('攤商名稱'), max_length=100)
    description = models.TextField(_('攤商介紹'), null=True, blank=True)
    contact_phone = models.CharField(_('攤商聯絡電話'), max_length=20)
    logo_url = models.URLField(_('Logo 圖片URL'), max_length=255, null=True, blank=True)
    logo_image = models.ImageField(_('攤商 Logo 圖示'), upload_to='stalls/', null=True, blank=True)
    
    # ✅ 新增：營業時間設定
    open_time = models.TimeField(_('開始營業時間'), default="08:00")
    close_time = models.TimeField(_('結束營業時間'), default="17:00")
    
    approval_status = models.CharField(_('平台審核狀態'), max_length=10, choices=APPROVAL_STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(_('是否營業中'), default=True)
    created_at = models.DateTimeField(_('註冊時間'), auto_now_add=True)

    class Meta:
        db_table = 'stalls'
        verbose_name = _('攤商')
        verbose_name_plural = _('攤商')

    def __str__(self):
        return self.name

# -----------------------------------------------------
# 4. 商品資訊表 (新增：實體圖片欄位)
# -----------------------------------------------------
class Product(models.Model):
    stall = models.ForeignKey(Stall, on_delete=models.CASCADE, verbose_name=_('所屬攤商'), related_name='products')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name=_('商品類別'), related_name='products')
    name = models.CharField(_('商品名稱'), max_length=255)
    description = models.TextField(_('商品描述'), null=True, blank=True)
    unit = models.CharField(_('規格/單位'), max_length=50)
    price = models.DecimalField(_('商品單價'), max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField(_('庫存數量'), default=0)
    
    # ✅ 新增：實體圖片上傳欄位
    image = models.ImageField(_('商品圖片'), upload_to='products/%Y/%m/', null=True, blank=True)
    image_url = models.URLField(_('備用圖片URL'), max_length=255, null=True, blank=True)
    
    status = models.CharField(_('商品狀態'), max_length=10, choices=PRODUCT_STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(_('上架時間'), auto_now_add=True)

    class Meta:
        db_table = 'products'
        verbose_name = _('商品')
        verbose_name_plural = _('商品')

    def __str__(self):
        return self.name

# -----------------------------------------------------
# 5. 購物車與地址 (補回 MemberAddress)
# -----------------------------------------------------
class CartItem(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name=_('會員'), related_name='cart_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_('商品'), related_name='cart_items')
    quantity = models.PositiveIntegerField(_('購買數量'))
    added_at = models.DateTimeField(_('加入時間'), auto_now_add=True)

    class Meta:
        db_table = 'cart_items'
        verbose_name = _('購物車項目')
        verbose_name_plural = _('購物車項目')
        unique_together = ('member', 'product')

class MemberAddress(models.Model):
    # ✅ 補回此模型，解決 admin.py 匯入報錯
    member = models.ForeignKey(Member, on_delete=models.CASCADE, verbose_name=_('會員'), related_name='addresses')
    address_line = models.CharField(_('詳細地址'), max_length=255, null=True, blank=True)

    class Meta:
        db_table = 'member_addresses'
        verbose_name = _('會員常用地址')
        verbose_name_plural = _('會員常用地址')

# -----------------------------------------------------
# 6. 訂單系統 (確保 related_name='sub_orders' 正確)
# -----------------------------------------------------
class ParentOrder(models.Model):
    member = models.ForeignKey(Member, on_delete=models.PROTECT, verbose_name=_('下單會員'), related_name='parent_orders')
    order_date = models.DateTimeField(_('下單時間'), auto_now_add=True)
    final_paid_amount = models.DecimalField(_('最終支付金額'), max_digits=10, decimal_places=2)
    payment_method = models.CharField(_('支付方式'), max_length=10, choices=PAYMENT_METHOD_CHOICES)
    order_status = models.CharField(_('父訂單狀態'), max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'parent_orders'
        verbose_name = _('顧客總訂單 (父訂單)')
        verbose_name_plural = _('顧客總訂單 (父訂單)')

class SubOrder(models.Model):
    # ✅ 確保 related_name='sub_orders' 以配合 Serializer 與 View 邏輯
    parent_order = models.ForeignKey(ParentOrder, on_delete=models.CASCADE, verbose_name=_('所屬父訂單'), related_name='sub_orders')
    stall = models.ForeignKey(Stall, on_delete=models.PROTECT, verbose_name=_('所屬攤商'), related_name='sub_orders')
    delivery_type = models.CharField(_('收貨方式'), max_length=10, choices=DELIVERY_TYPE_CHOICES)
    order_status = models.CharField(_('子訂單狀態'), max_length=20, choices=SUB_ORDER_STATUS_CHOICES, default='received')

    class Meta:
        db_table = 'sub_orders'
        verbose_name = _('攤商獨立訂單 (子訂單)')
        verbose_name_plural = _('攤商獨立訂單 (子訂單)')

class OrderItem(models.Model):
    sub_order = models.ForeignKey(SubOrder, on_delete=models.CASCADE, verbose_name=_('所屬子訂單'), related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name=_('商品'), related_name='order_details')
    unit_price_snapshot = models.DecimalField(_('訂購時的單價快照'), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_('購買數量'))

    class Meta:
        db_table = 'order_items'
        verbose_name = _('訂單商品明細')
        verbose_name_plural = _('訂單商品明細')