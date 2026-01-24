from django.urls import path
from .views import (
    BalanceSheetView, 
    AddCapitalView, 
    TransferToWalletView, 
    TreasuryListView, 
    CreateTreasuryView,
    P2PTransferView,   # NEW
    ATMWithdrawView    # NEW
)

urlpatterns = [
    path('balance-sheet/', BalanceSheetView.as_view(), name='balance-sheet'),
    path('treasuries/', TreasuryListView.as_view(), name='treasury-list'),
    path('treasuries/create/', CreateTreasuryView.as_view(), name='treasury-create'),
    path('add-capital/', AddCapitalView.as_view(), name='add-capital'),
    path('transfer-to-wallet/', TransferToWalletView.as_view(), name='transfer-to-wallet'),
    path('transfers/p2p/', P2PTransferView.as_view(), name='p2p-transfer'), # NEW
    path('withdraw/atm/', ATMWithdrawView.as_view(), name='atm-withdraw'),   # NEW
]
