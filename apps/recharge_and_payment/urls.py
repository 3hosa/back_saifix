from django.urls import path
from .views import (
    PaymentView,
    SubscriberBalanceView,
    OffersView,
    AgentBalanceView,
    TransactionStatusView
)

urlpatterns = [
    path('payment/', PaymentView.as_view(), name='alzajil-payment'),
    path('subscriber-balance/', SubscriberBalanceView.as_view(), name='alzajil-subscriber-balance'),
    path('offers/', OffersView.as_view(), name='alzajil-offers'),
    path('agent-balance/', AgentBalanceView.as_view(), name='alzajil-agent-balance'),
    path('transaction-status/', TransactionStatusView.as_view(), name='alzajil-transaction-status'),
]
