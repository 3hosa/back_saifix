from rest_framework import status, generics, views, parsers, serializers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .serializers import UserRegistrationSerializer, BroadcastNotificationSerializer
from .models import User, Notification, BroadcastNotification
from rest_framework import filters

class LoginView(views.APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({'error': 'يجب إدخال اسم المستخدم وكلمة المرور'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Try to authenticate
        user = authenticate(username=username, password=password)
        
        if user is None:
            # Try with phone number
            try:
                user_obj = User.objects.get(phone_number=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if user is not None:
            refresh = RefreshToken.for_user(user)
            return Response({
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': UserRegistrationSerializer(user).data
            })
        
        return Response({'error': 'اسم المستخدم أو كلمة المرور غير صحيحة'}, status=status.HTTP_401_UNAUTHORIZED)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            print("Registration Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()
        
        # Generate Tokens
        refresh = RefreshToken.for_user(user)
        
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "message": "تم إنشاء الحساب بنجاح.",
                "user": serializer.data,
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            },
            status=status.HTTP_201_CREATED,
            headers=headers
        )

class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'first_name', 'last_name', 'phone_number', 'alternative_phone']
    
    def get_queryset(self):
        # يمكن إضافة فلاتر هنا لاحقاً
        return User.objects.all().order_by('-date_joined')

class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def perform_update(self, serializer):
        user = self.get_object()
        
        # حماية حالة التوثيق: لا يمكن إلغاء التوثيق بعد اعتماده
        is_verified_input = self.request.data.get('is_verified')
        if user.is_verified and is_verified_input is False:
            raise serializers.ValidationError({"is_verified": "لا يمكن إلغاء توثيق حساب مفعل."})
            
        # السماح بتغيير حالة النشاط (الإيقاف) حتى للحسابات الموثقة
        serializer.save()

class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny] # In production this should be IsAdminUser

class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class KYCSubmissionView(views.APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def post(self, request, *args, **kwargs):
        user = request.user
        data = request.data
        
        # Debug: Print received data (without files)
        print("Received KYC Data:", {k: v for k, v in data.items() if not hasattr(v, 'read')})

        # Update fields manually to handle potential issues with serializer partial updates on files
        try:
            # Update Text Fields
            if 'id_type' in data: user.id_type = data['id_type']
            if 'id_number' in data: user.id_number = data['id_number']
            if 'issuer' in data: user.issuer = data['issuer']
            if 'nationality' in data: user.nationality = data['nationality']
            if 'place_of_birth' in data: user.place_of_birth = data['place_of_birth']
            if 'city' in data: user.city = data['city']
            if 'district' in data: user.district = data['district']
            if 'area' in data: user.area = data['area']
            if 'address' in data: user.address = data['address']
            
            # Helper to parse clean date strings
            def parse_date_str(d_str):
                if not d_str or d_str == 'null': return None
                # Flutter might send "2000-01-01 00:00:00.000" or "2000-01-01"
                return d_str.split(' ')[0]

            if 'issue_date' in data: user.issue_date = parse_date_str(data['issue_date'])
            if 'expiry_date' in data: user.expiry_date = parse_date_str(data['expiry_date'])
            if 'date_of_birth' in data: user.date_of_birth = parse_date_str(data['date_of_birth'])
            
            # Update Files
            if 'id_front' in request.FILES: user.id_front = request.FILES['id_front']
            if 'id_back' in request.FILES: user.id_back = request.FILES['id_back']
            if 'selfie' in request.FILES: user.selfie = request.FILES['selfie']
            
            user.save()
            return Response({"message": "تم رفع بيانات التوثيق بنجاح", "user": UserRegistrationSerializer(user).data}, status=status.HTTP_200_OK)
            
        except Exception as e:
            print("KYC Update Error:", str(e))
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class AdminPasswordResetView(views.APIView):
    permission_classes = [AllowAny] # In production this should be IsAdminUser

    def post(self, request, pk, *args, **kwargs):
        try:
            user = User.objects.get(pk=pk)
            user.set_password('123456')
            user.save()
            return Response({"message": "تم إعادة تعيين كلمة المرور إلى 123456 بنجاح"}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "المستخدم غير موجود"}, status=status.HTTP_404_NOT_FOUND)

class NotificationListView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = request.user.notifications.all()
        data = [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at
            } for n in notifications
        ]
        return Response(data)

class MarkNotificationsReadView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.notifications.update(is_read=True)
        return Response({"status": "success"})

class BroadcastNotificationCreateView(generics.CreateAPIView):
    queryset = BroadcastNotification.objects.all()
    serializer_class = BroadcastNotificationSerializer
    permission_classes = [AllowAny] # In production this should be restricted

class PublicBroadcastNotificationView(views.APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        latest = BroadcastNotification.objects.order_by('-created_at').first()
        if latest:
            return Response(BroadcastNotificationSerializer(latest).data)
        return Response({"detail": "No notifications found"}, status=status.HTTP_404_NOT_FOUND)
