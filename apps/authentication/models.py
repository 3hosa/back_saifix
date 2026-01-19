from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    GENDER_CHOICES = [
        ('M', 'ذكر'),
        ('F', 'أنثى'),
    ]

    ID_TYPE_CHOICES = [
        ('NATIONAL_ID', 'بطاقة شخصية'),
        ('PASSPORT', 'جواز سفر'),
    ]

    # الحقول الأساسية
    second_name = models.CharField(max_length=50, verbose_name="الاسم الثاني", blank=True)
    third_name = models.CharField(max_length=50, verbose_name="الاسم الثالث", blank=True)
    phone_number = models.CharField(max_length=20, unique=True, verbose_name="رقم الهاتف")
    alternative_phone = models.CharField(max_length=20, verbose_name="رقم الهاتف البديل", blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, verbose_name="الجنس")

    # بيانات الهوية (KYC)
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default='NATIONAL_ID', verbose_name="نوع الهوية")
    id_number = models.CharField(max_length=50, verbose_name="رقم الهوية", blank=True)
    issuer = models.CharField(max_length=100, verbose_name="جهة الإصدار", blank=True)
    issue_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الإصدار")
    expiry_date = models.DateField(null=True, blank=True, verbose_name="تاريخ الانتهاء")
    
    nationality = models.CharField(max_length=50, default="يمني", verbose_name="الجنسية")
    place_of_birth = models.CharField(max_length=100, verbose_name="مكان الميلاد", blank=True)
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاريخ الميلاد")

    # بيانات الإقامة
    city = models.CharField(max_length=100, verbose_name="المدينة", blank=True)
    district = models.CharField(max_length=100, verbose_name="المديرية", blank=True)
    area = models.CharField(max_length=100, verbose_name="المنطقة", blank=True)
    address = models.TextField(verbose_name="العنوان بالتفصيل", blank=True)

    # المستندات (الصور)
    id_front = models.ImageField(upload_to='ids/front/', null=True, blank=True, verbose_name="صورة الهوية - أمامي")
    id_back = models.ImageField(upload_to='ids/back/', null=True, blank=True, verbose_name="صورة الهوية - خلفي")
    selfie = models.ImageField(upload_to='ids/selfie/', null=True, blank=True, verbose_name="صورة سيلفي مع الهوية")

    # حالة الحساب
    is_verified = models.BooleanField(default=False, verbose_name="تم التحقق")
    is_active = models.BooleanField(default=False, verbose_name="نشط")

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمين"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name="المستخدم")
    title = models.CharField(max_length=255, verbose_name="العنوان")
    message = models.TextField(verbose_name="الرسالة")
    is_read = models.BooleanField(default=False, verbose_name="مقرؤة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ الإنشاء")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"

    def __str__(self):
        return f"{self.title} - {self.user.username}"
