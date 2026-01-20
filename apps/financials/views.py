from rest_framework import views, response, permissions, status
from django.db.models import Sum
from django.db import transaction
from decimal import Decimal
from .models import CompanyTreasury, CompanyTransaction
from apps.wallets.models import Wallet, Transaction
from apps.authentication.models import User

class BalanceSheetView(views.APIView):
    permission_classes = [permissions.AllowAny] # In prod: IsAdminUser

    def get(self, request):
        currencies = ['YER', 'USD', 'SAR']
        report = []
        
        for currency in currencies:
            # 1. Assets (Company Money)
            company_assets = CompanyTreasury.objects.filter(currency=currency).aggregate(total=Sum('balance'))['total'] or 0
            
            # 2. Liabilities (User Deposits)
            user_liabilities = Wallet.objects.filter(currency=currency).aggregate(total=Sum('balance'))['total'] or 0
            
            # 3. Net Position
            net_position = float(company_assets) - float(user_liabilities)
            
            report.append({
                'currency': currency,
                'assets': float(company_assets),
                'liabilities': float(user_liabilities),
                'net_position': net_position,
                'status': 'Surplus' if net_position >= 0 else 'Deficit'
            })

        return response.Response({
            'report': report,
            'details': {
                'treasuries': list(CompanyTreasury.objects.values('id', 'name', 'type', 'currency', 'balance'))
            }
        })

class AddCapitalView(views.APIView):
    """إضافة رأس مال إلى خزينة الشركة"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        treasury_id = request.data.get('treasury_id')
        amount = request.data.get('amount')
        description = request.data.get('description', 'إضافة رأس مال')
        
        # Ensure description is not empty
        if not description or description.strip() == '':
            description = 'إضافة رأس مال'

        try:
            if not treasury_id:
                return response.Response({'error': 'يرجى تحديد الخزينة'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not amount:
                return response.Response({'error': 'يرجى إدخال المبلغ'}, status=status.HTTP_400_BAD_REQUEST)
            
            amount = Decimal(str(amount))
            if amount <= 0:
                return response.Response({'error': 'المبلغ يجب أن يكون أكبر من صفر'}, status=status.HTTP_400_BAD_REQUEST)

            treasury = CompanyTreasury.objects.get(id=treasury_id)
            
            with transaction.atomic():
                treasury.balance += amount
                treasury.save()
                
                CompanyTransaction.objects.create(
                    treasury=treasury,
                    amount=amount,
                    description=description
                )

            return response.Response({
                'message': 'تم إضافة رأس المال بنجاح',
                'new_balance': float(treasury.balance)
            })

        except CompanyTreasury.DoesNotExist:
            return response.Response({'error': 'الخزينة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return response.Response({'error': f'خطأ في المبلغ: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TransferToWalletView(views.APIView):
    """تحويل أموال من خزينة الشركة إلى محفظة مستخدم"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        treasury_id = request.data.get('treasury_id')
        user_id = request.data.get('user_id')
        amount = request.data.get('amount')
        description = request.data.get('description', 'تحويل من الشركة')

        try:
            if not treasury_id:
                return response.Response({'error': 'يرجى تحديد الخزينة'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user_id:
                return response.Response({'error': 'يرجى إدخال رقم المستخدم'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not amount:
                return response.Response({'error': 'يرجى إدخال المبلغ'}, status=status.HTTP_400_BAD_REQUEST)
            
            amount = Decimal(str(amount))
            if amount <= 0:
                return response.Response({'error': 'المبلغ يجب أن يكون أكبر من صفر'}, status=status.HTTP_400_BAD_REQUEST)

            treasury = CompanyTreasury.objects.get(id=treasury_id)
            
            # Try to find user by ID first, then by phone number
            user = None
            try:
                # Try as integer ID first
                user_id_int = int(user_id)
                user = User.objects.filter(id=user_id_int).first()
            except (ValueError, TypeError):
                # Not a valid integer, skip ID lookup
                pass
            
            # If not found by ID, try by phone number
            if not user:
                user = User.objects.filter(phone_number=str(user_id)).first()
            
            if not user:
                return response.Response({
                    'error': f'المستخدم برقم {user_id} غير موجود. يرجى التأكد من رقم المستخدم أو رقم الهاتف.'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if treasury has enough balance
            if treasury.balance < amount:
                return response.Response({
                    'error': f'رصيد الخزينة غير كافٍ. الرصيد الحالي: {treasury.balance} {treasury.currency}'
                }, status=status.HTTP_400_BAD_REQUEST)

            # Get or create user wallet in same currency
            wallet, created = Wallet.objects.get_or_create(
                user=user,
                currency=treasury.currency,
                defaults={'balance': 0}
            )

            with transaction.atomic():
                # Deduct from treasury
                treasury.balance -= amount
                treasury.save()
                
                CompanyTransaction.objects.create(
                    treasury=treasury,
                    amount=-amount,
                    description=f"تحويل إلى محفظة {user.username}"
                )

                # Add to user wallet
                wallet.balance += amount
                wallet.save()
                
                Transaction.objects.create(
                    user=user,
                    amount=amount,
                    currency=treasury.currency,
                    transaction_type='DEPOSIT',
                    description=description
                )

            return response.Response({
                'message': 'تم التحويل بنجاح',
                'treasury_balance': float(treasury.balance),
                'wallet_balance': float(wallet.balance),
                'user_name': user.username
            })

        except CompanyTreasury.DoesNotExist:
            return response.Response({'error': 'الخزينة غير موجودة'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return response.Response({'error': f'خطأ في البيانات: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TreasuryListView(views.APIView):
    """قائمة جميع الخزائن"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        treasuries = CompanyTreasury.objects.all().values('id', 'name', 'type', 'currency', 'balance')
        return response.Response(list(treasuries))

class CreateTreasuryView(views.APIView):
    """إنشاء خزينة جديدة"""
    permission_classes = [permissions.AllowAny]  # In production: IsAdminUser

    def post(self, request):
        name = request.data.get('name')
        treasury_type = request.data.get('type')
        currency = request.data.get('currency')
        initial_balance = request.data.get('initial_balance', 0)

        try:
            initial_balance = Decimal(str(initial_balance))
            
            treasury = CompanyTreasury.objects.create(
                name=name,
                type=treasury_type,
                currency=currency,
                balance=initial_balance
            )

            if initial_balance > 0:
                CompanyTransaction.objects.create(
                    treasury=treasury,
                    amount=initial_balance,
                    description='رصيد افتتاحي'
                )

            return response.Response({
                'message': 'تم إنشاء الخزينة بنجاح',
                'id': treasury.id,
                'name': treasury.name
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
