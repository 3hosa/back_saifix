from django.db import models

class CompanyTreasury(models.Model):
    CURRENCY_CHOICES = [
        ('YER', 'رال يمني'),
        ('USD', 'دولار أمريكي'),
        ('SAR', 'ريال سعودي'),
    ]
    
    TYPE_CHOICES = [
        ('CASH', 'خزينة نقدية'),
        ('BANK', 'حساب بنكي'),
    ]

    name = models.CharField(max_length=100, verbose_name="اسم الحساب/الخزنة")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, verbose_name="النوع")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, verbose_name="العملة")
    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, verbose_name="الرصيد الحالي")
    
    class Meta:
        verbose_name = "خزينة/حساب بنكي"
        verbose_name_plural = "أصول الشركة (خزائن وبنوك)"

    def __str__(self):
        return f"{self.name} ({self.currency})"

class CompanyTransaction(models.Model):
    treasury = models.ForeignKey(CompanyTreasury, on_delete=models.CASCADE, related_name='transactions', verbose_name="الخزينة/الحساب")
    amount = models.DecimalField(max_digits=20, decimal_places=2, verbose_name="المبلغ")
    description = models.CharField(max_length=255, verbose_name="الوصف")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="التاريخ")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "حركة مالية للشركة"
        verbose_name_plural = "سجل حركات الشركة"

    def __str__(self):
        return f"{self.description} - {self.amount}"
