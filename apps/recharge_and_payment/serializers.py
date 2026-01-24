from rest_framework import serializers

class BaseAlzajilSerializer(serializers.Serializer):
    """
    مياليزر أساسي للتحقق المشترك.
    يتم التعامل مع USR و TKN في الخلفية، وليس من العميل.
    """
    pass

class PaymentSerializer(BaseAlzajilSerializer):
    AC = serializers.IntegerField(help_text="رمز الإجراء: 7100 (سداد)، 7200 (عروض)، إلخ")
    SC = serializers.IntegerField(help_text="رمز الخدمة من الجدول 1.2")
    AMT = serializers.FloatField(required=False, help_text="المبلغ (لعمليات السداد)")
    SNO = serializers.CharField(max_length=15, help_text="رقم المشترك")
    MT = serializers.IntegerField(required=False, help_text="نوع المشترك: 0 (دفع مسبق)، 1 (فوترة)")
    REF = serializers.CharField(max_length=100, required=False, help_text="رقم مرجع فريد من الوكيل")
    SAC = serializers.CharField(max_length=20, required=False, help_text="رمز منطقة الخدمة أو معرف العرض")
    REM = serializers.CharField(max_length=100, required=False, help_text="ملاحظات")
    item = serializers.IntegerField(required=False, help_text="رمز العنصر/الخدمة الفرعي من الجدول 1.7")
    SOI = serializers.CharField(required=False, help_text="قيمة JSON إضافية لخدمات الترفيه (AC=7700)")
    COST = serializers.FloatField(required=False, help_text="التكلفة للتحقق")

    def validate(self, data):
        # منطق التحقق الأساسي
        # مثال: إذا كان AC هو 7200، فإن SAC (معرف العرض) مطلوب.
        if data.get('AC') == 7200 and not data.get('SAC'):
            raise serializers.ValidationError({"SAC": "هذا الحقل مطلوب للعروض (AC=7200)."})
        return data

class BalanceQuerySerializer(BaseAlzajilSerializer):
    """
    لرمز الإجراء AC 4001 (الاستعلام عن الرصيد)
    """
    AC = serializers.IntegerField(required=False, help_text="رمز الإجراء (اختياري، الافتراضي 4001)")
    SC = serializers.IntegerField(help_text="رمز الخدمة")
    SNO = serializers.CharField(max_length=15, help_text="رقم المشترك")

class OfferManagementSerializer(BaseAlzajilSerializer):
    """
    لرموز الإجراء AC 4002-4007 (إدارة العروض والاستعلام عنها)
    """
    AC = serializers.IntegerField(help_text="رمز الإجراء: 4002-4007 (4005 للقائمة، 4006 للقائمة+رصيد)")
    SC = serializers.IntegerField(help_text="رمز الخدمة (مثل 42103 ليمن موبايل)")
    SNO = serializers.CharField(max_length=9, help_text="رقم المشترك")
    SAC = serializers.CharField(max_length=10, required=False, help_text="معرف العرض. فارغ في حالة 4005, 4006, 4007")

class TransactionStatusSerializer(BaseAlzajilSerializer):
    """
    لرمز الإجراء AC 1003 (حالة المعاملة)
    """
    REF = serializers.CharField(max_length=100, help_text="مرجع المعاملة من الطلب السابق")
