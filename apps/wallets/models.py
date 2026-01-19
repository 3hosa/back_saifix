from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator

class Wallet(models.Model):
    CURRENCY_CHOICES = [
        ('YER', 'ريال يمني'),
        ('USD', 'دولار أمريكي'),
        ('SAR', 'ريال سعودي'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallets',
        verbose_name="المستخدم"
    )
    balance = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0)],
        verbose_name="الرصيد"
    )
    currency = models.CharField(
        max_length=3, 
        choices=CURRENCY_CHOICES, 
        default='YER', 
        verbose_name="العملة"
    )
    is_active = models.BooleanField(default=False, verbose_name="نشطة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")

    class Meta:
        verbose_name = "محفظة"
        verbose_name_plural = "المحافظ"
        unique_together = ['user', 'currency']

    def __str__(self):
        return f"محفظة {self.user.first_name} - {self.currency}"

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'إيداع'),
        ('WITHDRAW', 'سحب'),
        ('TRANSFER', 'تحويل P2P'),
        ('EXCHANGE', 'صرافة'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Wallet.CURRENCY_CHOICES)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='SUCCESS')
    reference_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="الرقم المرجعي")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For P2P
    to_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_transactions')

    def save(self, *args, **kwargs):
        if not self.reference_number:
            # Generate unique reference number: TRX-YYYYMMDD-XXXXXX
            import datetime
            import random
            import string
            date_part = datetime.datetime.now().strftime('%Y%m%d')
            random_part = ''.join(random.choices(string.digits, k=6))
            self.reference_number = f"TRX-{date_part}-{random_part}"
            
            # Ensure uniqueness
            while Transaction.objects.filter(reference_number=self.reference_number).exists():
                random_part = ''.join(random.choices(string.digits, k=6))
                self.reference_number = f"TRX-{date_part}-{random_part}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount} {self.currency} - {self.reference_number}"

class ExchangeRate(models.Model):
    """أسعار الصرف بين العملات"""
    CURRENCY_CHOICES = [
        ('YER', 'ريال يمني'),
        ('USD', 'دولار أمريكي'),
        ('SAR', 'ريال سعودي'),
    ]
    
    from_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, verbose_name="من عملة")
    to_currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, verbose_name="إلى عملة")
    buy_rate = models.DecimalField(max_digits=20, decimal_places=6, verbose_name="سعر الشراء")
    sell_rate = models.DecimalField(max_digits=20, decimal_places=6, verbose_name="سعر البيع")
    is_active = models.BooleanField(default=True, verbose_name="نشط")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخر تحديث")
    
    class Meta:
        unique_together = ['from_currency', 'to_currency']
        verbose_name = "سعر صرف"
        verbose_name_plural = "أسعار الصرف"
    
    def __str__(self):
        return f"{self.from_currency} → {self.to_currency}: {self.buy_rate}"

class CurrencyConversion(models.Model):
    """سجل عمليات تحويل العملات"""
    STATUS_CHOICES = [
        ('PENDING', 'قيد المعالجة'),
        ('COMPLETED', 'مكتمل'),
        ('FAILED', 'فشل'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='conversions', verbose_name="المستخدم")
    from_currency = models.CharField(max_length=3, verbose_name="من عملة")
    to_currency = models.CharField(max_length=3, verbose_name="إلى عملة")
    amount_sent = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="المبلغ المرسل")
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=6, verbose_name="سعر الصرف المستخدم")
    amount_received = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="المبلغ المستلم")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="الحالة")
    reference_number = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="الرقم المرجعي")
    notes = models.TextField(blank=True, verbose_name="ملاحظات")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "عملية تحويل عملة"
        verbose_name_plural = "عمليات تحويل العملات"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            # Generate unique reference number: EXC-YYYYMMDD-XXXXXX
            import datetime
            import random
            import string
            date_part = datetime.datetime.now().strftime('%Y%m%d')
            random_part = ''.join(random.choices(string.digits, k=6))
            self.reference_number = f"EXC-{date_part}-{random_part}"
            
            # Ensure uniqueness
            while CurrencyConversion.objects.filter(reference_number=self.reference_number).exists():
                random_part = ''.join(random.choices(string.digits, k=6))
                self.reference_number = f"EXC-{date_part}-{random_part}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username}: {self.amount_sent} {self.from_currency} → {self.amount_received} {self.to_currency} - {self.reference_number}"
