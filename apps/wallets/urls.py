from django.urls import path
from .views import (
    WalletBalanceView, 
    ExchangeRateView, 
    ExchangeRateManageView,
    TransactionListView, 
    P2PTransferView, 
    ConvertCurrencyView,
    ConversionHistoryView
)

urlpatterns = [
    path('balance/', WalletBalanceView.as_view(), name='wallet-balance'),
    path('rates/', ExchangeRateView.as_view(), name='exchange-rates'),
    path('rates/manage/', ExchangeRateManageView.as_view(), name='exchange-rates-manage'),
    path('transactions/', TransactionListView.as_view(), name='transactions'),
    path('transfer-p2p/', P2PTransferView.as_view(), name='transfer-p2p'),
    path('convert/', ConvertCurrencyView.as_view(), name='convert-currency'),
    path('conversions/', ConversionHistoryView.as_view(), name='conversion-history'),
]
