from rest_framework import serializers
from .models import User

class UserRegistrationSerializer(serializers.ModelSerializer):
    wallets = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'second_name', 'third_name', 'last_name',
            'full_name', 'phone_number', 'alternative_phone', 'gender', 'password', 
            'is_active', 'is_verified',
            'wallets', # New field for balances
            # حقول KYC نجعلها اختيارية في مرحلة التسجيل الأولي
            'id_type', 'id_number', 'issuer', 'issue_date', 'expiry_date',
            'nationality', 'place_of_birth', 'date_of_birth',
            'city', 'district', 'area', 'address',
            'id_front', 'id_back', 'selfie'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'username': {'required': False}, # سنقوم بتوليده تلقائياً
            'alternative_phone': {'required': False},
            # جعل حقول الهوية اختيارية
            'id_type': {'required': False}, 'id_number': {'required': False}, 
            'issuer': {'required': False}, 'issue_date': {'required': False}, 
            'expiry_date': {'required': False}, 'nationality': {'required': False},
            'place_of_birth': {'required': False}, 'date_of_birth': {'required': False},
            'city': {'required': False}, 'district': {'required': False},
            'area': {'required': False}, 'address': {'required': False},
            'id_front': {'required': False}, 'id_back': {'required': False},
            'selfie': {'required': False},
            'wallets': {'read_only': True},
            'full_name': {'read_only': True},
        }

    def get_full_name(self, obj):
        """إرجاع الاسم الكامل"""
        names = [obj.first_name, obj.second_name, obj.third_name, obj.last_name]
        return ' '.join([n for n in names if n])
    
    def get_wallets(self, obj):
        """إرجاع أرصدة المحافظ"""
        data = { 'YER': 0.0, 'USD': 0.0, 'SAR': 0.0 }
        if hasattr(obj, 'wallets'):
            # Get all wallets regardless of is_active status
            all_wallets = obj.wallets.all()
            print(f"👤 User {obj.username} has {all_wallets.count()} wallets")
            
            for w in all_wallets:
                data[w.currency] = float(w.balance)
                print(f"   💰 {w.currency}: {w.balance} (active: {w.is_active})")
        
        print(f"✅ Returning wallets: {data}")
        return data

    def to_internal_value(self, data):
        data = data.copy() # Make a mutable copy
        # تحويل camelCase (من فلاتر) إلى snake_case (للجانغو)
        if 'firstName' in data: data['first_name'] = data.pop('firstName')
        if 'secondName' in data: data['second_name'] = data.pop('secondName')
        if 'thirdName' in data: data['third_name'] = data.pop('thirdName')
        if 'lastName' in data: data['last_name'] = data.pop('lastName')
        if 'phone' in data: data['phone_number'] = data.pop('phone')
        
        # تعيين username ليكون نفس رقم الهاتف إذا لم يتم إرساله
        if 'username' not in data and 'phone_number' in data:
            data['username'] = data['phone_number']
        
        return super().to_internal_value(data)

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

class BroadcastNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BroadcastNotification
        fields = ['id', 'title', 'message', 'created_at']
