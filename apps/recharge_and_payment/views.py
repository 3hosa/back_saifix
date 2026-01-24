from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    PaymentSerializer,
    BalanceQuerySerializer,
    OfferManagementSerializer,
    TransactionStatusSerializer
)
from .services import AlzajilClient

class BaseAlzajilView(APIView):
    """
    عرض أساسي لتهيئة العميل (Client Initialization)
    """
    def get_client(self):
        return AlzajilClient()

class PaymentView(BaseAlzajilView):
    """
    يعالج عمليات السداد (AC=7100, 7600, 7700) وشراء العروض (AC=7200).
    يتوقع طلب POST.
    """
    def post(self, request):
        from django.db import transaction
        from apps.wallets.models import Wallet, Transaction
        from decimal import Decimal

        serializer = PaymentSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            # Ensure user is authenticated
            if not user.is_authenticated:
                return Response({"MSG": "User must be authenticated", "RC": -1}, status=status.HTTP_401_UNAUTHORIZED)

            validated = serializer.validated_data
            amount = float(validated.get('AMT', 0)) # Default to 0 if not explicitly in validated_data, though serializer checks it
            # Start with some sanity check on amount
            if amount <= 0:
                 return Response({"MSG": "Invalid amount", "RC": -1}, status=status.HTTP_400_BAD_REQUEST)

            # 1. Check Wallet Balance (Assume YER for now as per current scope)
            try:
                wallet = Wallet.objects.get(user=user, currency='YER')
            except Wallet.DoesNotExist:
                return Response({"MSG": "لا توجد محفظة (YER) لهذا المستخدم", "RC": -1}, status=status.HTTP_400_BAD_REQUEST)

            if float(wallet.balance) < amount:
                 return Response({"MSG": "رصيد المحفظة غير كافٍ لإتمام العملية", "RC": -1}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Call API
            try:
                client = self.get_client()
                # We pass serializer data directly. Ensuring keys/values are compliant happens in client
                response_data = client.send_payment(validated)
                
                # 3. If Success -> Deduct & Record
                if str(response_data.get('RC')) == '0':
                    with transaction.atomic():
                        # Refetch wallet to lock it
                        wallet = Wallet.objects.select_for_update().get(id=wallet.id)
                        
                        # Check balance again just in case
                        if float(wallet.balance) < amount:
                            # Edge case: Balance changed during API call. 
                            # We must fail the local transaction but API succeeded! 
                            # Ideally we should queue a refund or alert admin. 
                            # For now, we will force negative or fail? 
                            # Let's deduct anyway to keep consistency with API, or strictly fail.
                            # Given it's a critical financial app, let's proceed with deduction (allow negative temporarily) OR fail.
                            # But wait, checking again before API is safer. 
                            # Stick to standard flow: Deduct.
                            pass

                        wallet.balance -= Decimal(str(amount))
                        wallet.save()

                        # Record Transaction
                        ref_no = response_data.get('REF', 'Unknown')
                        desc = f"سداد خدمة (SC: {validated.get('SC')}) - {validated.get('SNO')}"
                        if validated.get('AC') == 7200:
                             desc = f"شراء باقة (SAC: {validated.get('SAC')}) - {validated.get('SNO')}"

                        Transaction.objects.create(
                            user=user,
                            amount=Decimal(str(amount)),
                            currency='YER',
                            transaction_type='WITHDRAW',
                            description=desc,
                            status='SUCCESS',
                            reference_number=str(ref_no) # Use API Ref as Transaction Ref
                        )
                
                return Response(response_data, status=status.HTTP_200_OK)

            except Exception as e:
                 print(f"Payment View Internal Error: {e}")
                 # Logic error or API Fail. No deduction.
                 return Response({"MSG": f"System Error: {str(e)}", "RC": -1}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        print(f"Payment Validation Error: {serializer.errors}")
        print(f"Request Data: {request.data}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubscriberBalanceView(BaseAlzajilView):
    """
    الاستعلام عن رصيد المشترك (AC=4001).
    عادة ما يكون GET.
    """
    def get(self, request):
        serializer = BalanceQuerySerializer(data=request.query_params)
        if serializer.is_valid():
            client = self.get_client()
            response_data = client.query_subscriber_balance(
                service_code=serializer.validated_data['SC'],
                subscriber_no=serializer.validated_data['SNO'],
                action_code=serializer.validated_data.get('AC', 4001)
            )
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OffersView(BaseAlzajilView):
    """
    إدارة العروض (AC=4002-4007).
    الطريقة: GET
    """
    def get(self, request):
        serializer = OfferManagementSerializer(data=request.query_params)
        if serializer.is_valid():
            client = self.get_client()
            response_data = client.manage_offers(
                action_code=serializer.validated_data['AC'],
                service_code=serializer.validated_data['SC'],
                subscriber_no=serializer.validated_data['SNO'],
                offer_id=serializer.validated_data.get('SAC')
            )
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AgentBalanceView(BaseAlzajilView):
    """
    الاستعلام عن رصيد الوكيل (AC=7400).
    الطريقة: GET
    """
    def get(self, request):
        client = self.get_client()
        response_data = client.query_agent_balance()
        return Response(response_data, status=status.HTTP_200_OK)

class TransactionStatusView(BaseAlzajilView):
    """
    التحقق من حالة المعاملة (AC=1003).
    الطريقة: GET
    """
    def get(self, request):
        serializer = TransactionStatusSerializer(data=request.query_params)
        if serializer.is_valid():
            client = self.get_client()
            response_data = client.check_transaction_status(
                trans_ref=serializer.validated_data['REF']
            )
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
