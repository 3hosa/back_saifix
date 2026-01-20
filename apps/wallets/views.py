from rest_framework import views, response, permissions, status, generics
from django.db.models import Sum
from django.db import transaction
from .models import Wallet, Transaction, ExchangeRate, CurrencyConversion
from apps.authentication.models import User

class WalletBalanceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        print(f" طلب الأرصدة من المستخدم: {user.username}")

        wallets_all = Wallet.objects.filter(user=user)
        wallets_active = wallets_all.filter(is_active=True)
        print(f" عدد المحافظ: الكل={wallets_all.count()} | النشطة={wallets_active.count()}")

        balances = {}
        for w in wallets_all:
            # آخر قيمة هي الأحدث إن تكررت العملة (ليس متوقعاً عادة)
            balances[w.currency] = float(w.balance)
            print(f"    {w.currency}: {w.balance} (active: {w.is_active})")

        # Ensure all currencies exist
        for currency in ['YER', 'USD', 'SAR']:
            if currency not in balances:
                balances[currency] = 0.0

        print(f"✅ Returning wallets: {balances}")
        return response.Response(balances)

class ExchangeRateView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        rates = ExchangeRate.objects.filter(is_active=True)
        data = [
            {
                'from_currency': r.from_currency,
                'to_currency': r.to_currency,
                'buy_rate': str(r.buy_rate),
                'sell_rate': str(r.sell_rate),
            }
            for r in rates
        ]
        return response.Response(data)

class ExchangeRateManageView(generics.ListCreateAPIView):
    """إدارة أسعار الصرف - للإدارة فقط"""
    permission_classes = [permissions.AllowAny]  # In production: IsAdminUser
    queryset = ExchangeRate.objects.all()
    
    def get(self, request):
        rates = self.queryset.all()
        data = [
            {
                'id': r.id,
                'from_currency': r.from_currency,
                'to_currency': r.to_currency,
                'buy_rate': str(r.buy_rate),
                'sell_rate': str(r.sell_rate),
                'is_active': r.is_active,
            }
            for r in rates
        ]
        return response.Response(data)
    
    def post(self, request):
        from_curr = request.data.get('from_currency')
        to_curr = request.data.get('to_currency')
        buy_rate = request.data.get('buy_rate')
        sell_rate = request.data.get('sell_rate')
        
        try:
            rate, created = ExchangeRate.objects.update_or_create(
                from_currency=from_curr,
                to_currency=to_curr,
                defaults={
                    'buy_rate': buy_rate,
                    'sell_rate': sell_rate,
                    'is_active': True
                }
            )
            return response.Response({
                'message': 'تم إضافة/تحديث سعر الصرف بنجاح',
                'id': rate.id
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TransactionListView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        user = request.user
        
        # Admin can view other user's transactions
        target_user_id = request.GET.get('user_id')
        if target_user_id and (request.user.is_staff or True): # True for testing/demo as requested
            try:
                user = User.objects.get(id=target_user_id)
            except User.DoesNotExist:
                return response.Response({'error': 'المستخدم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        
        # Pagination parameters
        try:
            limit = int(request.GET.get('limit', 15))
            offset = int(request.GET.get('offset', 0))
        except ValueError:
            limit = 15
            offset = 0

        # Filter parameters
        currency = request.GET.get('currency')
        trx_type = request.GET.get('type')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # Base Query - exclude individual exchange legs as we will use CurrencyConversion for a unified view
        queryset = Transaction.objects.filter(user=user).exclude(transaction_type='EXCHANGE').select_related('to_user').order_by('-created_at')

        # Apply Filters to Transactions
        if currency and currency != 'all':
            queryset = queryset.filter(currency=currency)
        
        if trx_type and trx_type != 'all':
            if trx_type == 'EXCHANGE':
                # If specifically looking for EXCHANGE, we will handle it via CurrencyConversion
                queryset = queryset.none()
            else:
                queryset = queryset.filter(transaction_type=trx_type)

        if start_date:
            from django.utils.dateparse import parse_date
            sd = parse_date(start_date)
            if sd:
                queryset = queryset.filter(created_at__date__gte=sd)

        if end_date:
            from django.utils.dateparse import parse_date
            ed = parse_date(end_date)
            if ed:
                queryset = queryset.filter(created_at__date__lte=ed)

        # Fetch CurrencyConversions if relevant
        conversions_data = []
        if not trx_type or trx_type == 'all' or trx_type == 'EXCHANGE':
            from django.db.models import Q
            conv_qs = CurrencyConversion.objects.filter(user=user).order_by('-created_at')
            
            # Apply filters to conversions
            if currency and currency != 'all':
                conv_qs = conv_qs.filter(Q(from_currency=currency) | Q(to_currency=currency))
            
            if start_date:
                from django.utils.dateparse import parse_date
                sd = parse_date(start_date)
                if sd:
                    conv_qs = conv_qs.filter(created_at__date__gte=sd)
            
            if end_date:
                from django.utils.dateparse import parse_date
                ed = parse_date(end_date)
                if ed:
                    conv_qs = conv_qs.filter(created_at__date__lte=ed)
            
            # Convert to standardized format
            for c in conv_qs[:offset + limit]: # Fetch enough to merge
                conversions_data.append({
                    'id': f"conv_{c.id}",
                    'reference_number': c.reference_number,
                    'type': 'EXCHANGE',
                    'direction': 'EXCHANGE',
                    'amount': float(c.amount_sent),
                    'currency': c.from_currency,
                    'target_amount': float(c.amount_received),
                    'target_currency': c.to_currency,
                    'exchange_rate': float(c.exchange_rate),
                    'description': f"صارفة من {c.from_currency} إلى {c.to_currency}",
                    'created_at': c.created_at.isoformat(),
                    'status': 'SUCCESS' if c.status == 'COMPLETED' else c.status,
                    'other_party_name': "",
                    'other_party_phone': "",
                })

        # Fetch Transactions
        transactions_data = []
        for t in queryset[:offset + limit]:
            ref_no = t.reference_number or f"TRX-{t.id}"
            other_party_name = ""
            other_party_phone = ""
            if t.to_user:
                other_party_phone = t.to_user.phone_number or ""
                other_party_name = f"{t.to_user.first_name} {t.to_user.last_name}".strip()
                if not other_party_name:
                    other_party_name = t.to_user.username

            direction = "IN"
            if t.transaction_type == 'DEPOSIT':
                direction = "IN"
            elif t.transaction_type == 'WITHDRAW':
                direction = "OUT"
            elif t.transaction_type == 'TRANSFER':
                direction = "OUT" if "إلى" in (t.description or "") else "IN"

            transactions_data.append({
                'id': t.id,
                'reference_number': ref_no,
                'type': t.transaction_type,
                'direction': direction,
                'amount': float(t.amount),
                'currency': t.currency,
                'description': t.description,
                'created_at': t.created_at.isoformat(),
                'status': t.status,
                'other_party_name': other_party_name,
                'other_party_phone': other_party_phone,
            })

        # Merge and Sort
        all_data = transactions_data + conversions_data
        all_data.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply global pagination
        final_data = all_data[offset : offset + limit]
        
        return response.Response(final_data)

class P2PTransferView(views.APIView):
    """تحويل بين محفظتين (نفس العملة أو مختلفة)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        sender = request.user
        phone = request.data.get('phone')
        recipient_id = request.data.get('recipient_id')
        amount = request.data.get('amount')
        currency = request.data.get('currency', 'YER')
        description = request.data.get('description', 'تحويل P2P')

        print("\n" + "-"*60)
        print(f"🔁 طلب تحويل P2P من: {sender.username}")
        print(f"📦 البيانات: phone={phone}, recipient_id={recipient_id}, amount={amount}, currency={currency}")
        try:
            amount = float(amount)
            if amount <= 0:
                return response.Response({'error': 'المبلغ يجب أن يكون أكبر من صفر'}, status=status.HTTP_400_BAD_REQUEST)

            # Find recipient by phone or ID
            recipient = None
            if phone:
                normalized = str(phone).replace(' ', '')
                digits = ''.join([c for c in normalized if c.isdigit()])
                last9 = digits[-9:] if len(digits) >= 9 else digits
                # Try exact first, then endswith 9 digits
                recipient = User.objects.filter(phone_number=digits).first()
                if not recipient:
                    recipient = User.objects.filter(phone_number__endswith=last9).exclude(id=sender.id).first()
                if not recipient:
                    return response.Response({'error': 'المستخدم المستلم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
            elif recipient_id:
                recipient = User.objects.get(id=recipient_id)
            else:
                return response.Response({'error': 'يجب تحديد رقم الهاتف أو معرف المستخدم'}, status=status.HTTP_400_BAD_REQUEST)

            if recipient.id == sender.id:
                return response.Response({'error': 'لا يمكن التحويل إلى نفسك'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get sender wallet - prioritize wallet with balance if duplicates exist
            sender_wallet = Wallet.objects.filter(user=sender, currency=currency).order_by('-balance').first()
            if not sender_wallet:
                return response.Response({'error': 'محفظة المرسل غير موجودة'}, status=status.HTTP_400_BAD_REQUEST)

            from decimal import Decimal
            bal_dec = Decimal(str(sender_wallet.balance))
            amt_dec = Decimal(str(amount))
            print(f"💰 محفظة #{sender_wallet.id} ({currency}): {bal_dec} | المطلوب: {amt_dec}")
            if bal_dec < amt_dec:
                return response.Response({'error': 'insufficient_funds'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create recipient wallet
            recipient_wallet, _ = Wallet.objects.get_or_create(
                user=recipient,
                currency=currency,
                defaults={'balance': 0, 'is_active': True}
            )

            with transaction.atomic():
                # Deduct from sender
                sender_wallet.balance = Decimal(str(sender_wallet.balance)) - Decimal(str(amount))
                sender_wallet.save()
                
                sender_transaction = Transaction.objects.create(
                    user=sender,
                    amount=Decimal(str(amount)),
                    currency=currency,
                    transaction_type='TRANSFER',
                    to_user=recipient,
                    description=f"تحويل إلى {recipient.username}",
                    status='SUCCESS'
                )

                # Add to recipient
                recipient_wallet.balance = Decimal(str(recipient_wallet.balance)) + Decimal(str(amount))
                recipient_wallet.save()
                
                Transaction.objects.create(
                    user=recipient,
                    amount=Decimal(str(amount)),
                    currency=currency,
                    transaction_type='TRANSFER',
                    to_user=sender,
                    description=f"استلام من {sender.username}",
                    status='SUCCESS'
                )

            return response.Response({
                'message': 'تم التحويل بنجاح',
                'new_balance': float(sender_wallet.balance),
                'reference_number': sender_transaction.reference_number,
                'id': sender_transaction.id
            })

        except User.DoesNotExist:
            return response.Response({'error': 'المستخدم المستلم غير موجود'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConvertCurrencyView(views.APIView):
    """تحويل عملة (صرافة) للمستخدم نفسه"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        print(f"\n{'='*60}")
        print(f" طلب تحويل عملة من المستخدم: {user.username}")
        print(f" البيانات المستلمة: {request.data}")
        
        from_currency = request.data.get('from_currency')
        to_currency = request.data.get('to_currency')
        amount = request.data.get('amount')

        print(f"   من عملة: {from_currency}")
        print(f"   إلى عملة: {to_currency}")
        print(f"   المبلغ: {amount}")

        if not all([from_currency, to_currency, amount]):
            print(f" بيانات غير مكتملة")
            return response.Response({'error': 'بيانات غير مكتملة'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            amount = float(amount)
            print(f" المبلغ بعد التحويل: {amount}")
            
            # Get exchange rate
            rate_obj = ExchangeRate.objects.filter(
                from_currency=from_currency,
                to_currency=to_currency,
                is_active=True
            ).first()

            if not rate_obj:
                return response.Response({'error': 'سعر الصرف غير متوفر'}, status=status.HTTP_400_BAD_REQUEST)

            # Calculate received amount
            exchange_rate = float(rate_obj.buy_rate)
            amount_received = amount * exchange_rate

            # Get sender wallet
            from_wallet = Wallet.objects.filter(user=user, currency=from_currency).first()
            if not from_wallet or from_wallet.balance < amount:
                return response.Response({'error': 'insufficient_funds'}, status=status.HTTP_400_BAD_REQUEST)

            # Get or create recipient wallet
            to_wallet, _ = Wallet.objects.get_or_create(
                user=user,
                currency=to_currency,
                defaults={'balance': 0, 'is_active': True}
            )

            from decimal import Decimal
            
            with transaction.atomic():
                # Deduct from source currency
                from_wallet.balance = from_wallet.balance - Decimal(str(amount))
                from_wallet.save()
                
                Transaction.objects.create(
                    user=user,
                    amount=amount,
                    currency=from_currency,
                    transaction_type='EXCHANGE',
                    description=f"صرف إلى {to_currency}",
                    status='SUCCESS'
                )

                # Add to target currency
                to_wallet.balance = to_wallet.balance + Decimal(str(amount_received))
                to_wallet.save()
                
                Transaction.objects.create(
                    user=user,
                    amount=amount_received,
                    currency=to_currency,
                    transaction_type='EXCHANGE',
                    description=f"صرف من {from_currency}",
                    status='SUCCESS'
                )

                # Record conversion
                conversion = CurrencyConversion.objects.create(
                    user=user,
                    from_currency=from_currency,
                    to_currency=to_currency,
                    amount_sent=amount,
                    exchange_rate=exchange_rate,
                    amount_received=amount_received,
                    status='COMPLETED'
                )

            return response.Response({
                'message': 'تمت عملية الصرف بنجاح',
                'amount_received': amount_received,
                'new_balance_from': float(from_wallet.balance),
                'new_balance_to': float(to_wallet.balance),
                'reference_number': conversion.reference_number,
                'id': conversion.id
            })

        except Exception as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ConversionHistoryView(views.APIView):
    """سجل عمليات صرف العملات"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        conversions = CurrencyConversion.objects.filter(user=request.user)[:50]
        data = [
            {
                'id': c.id,
                'reference_number': c.reference_number,
                'from_currency': c.from_currency,
                'to_currency': c.to_currency,
                'amount_sent': float(c.amount_sent),
                'amount_received': float(c.amount_received),
                'exchange_rate': float(c.exchange_rate),
                'status': c.status,
                'created_at': c.created_at.isoformat(),
            }
            for c in conversions
        ]
        return response.Response(data)
