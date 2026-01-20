from django.contrib import admin
from .models import CompanyTreasury, CompanyTransaction

@admin.register(CompanyTreasury)
class CompanyTreasuryAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'currency', 'balance')
    list_filter = ('type', 'currency')
    search_fields = ('name',)

@admin.register(CompanyTransaction)
class CompanyTransactionAdmin(admin.ModelAdmin):
    list_display = ('treasury', 'amount', 'description', 'created_at')
    list_filter = ('treasury', 'created_at')
    search_fields = ('description',)
    date_hierarchy = 'created_at'
