from django.contrib import admin
from .models import Wallet, Transaction, ExchangeRate, CurrencyConversion

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'currency', 'balance', 'is_active', 'created_at')
    list_filter = ('currency', 'is_active')
    search_fields = ('user__username', 'user__phone_number')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'transaction_type', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('transaction_type', 'currency', 'status')
    search_fields = ('user__username', 'description')
    date_hierarchy = 'created_at'

@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('from_currency', 'to_currency', 'buy_rate', 'sell_rate', 'is_active', 'updated_at')
    list_filter = ('from_currency', 'to_currency', 'is_active')
    
@admin.register(CurrencyConversion)
class CurrencyConversionAdmin(admin.ModelAdmin):
    list_display = ('user', 'from_currency', 'to_currency', 'amount_sent', 'amount_received', 'status', 'created_at')
    list_filter = ('from_currency', 'to_currency', 'status')
    search_fields = ('user__username',)
    date_hierarchy = 'created_at'
