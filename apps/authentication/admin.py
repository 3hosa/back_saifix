from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import User, Notification, BroadcastNotification

class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['username', 'phone_number', 'first_name', 'last_name', 'is_verified', 'is_active', 'display_id_status']
    list_filter = ['is_verified', 'is_active', 'gender', 'id_type']
    
    fieldsets = UserAdmin.fieldsets + (
        ('بيانات الهوية والتحقق', {'fields': (
            'id_type', 'id_number', 'issuer', 'issue_date', 'expiry_date',
            'nationality', 'place_of_birth', 'date_of_birth', 'is_verified'
        )}),
        ('بيانات الإقامة', {'fields': ('city', 'district', 'area', 'address')}),
        ('وثائق المستخدم', {'fields': ('id_front', 'id_back', 'selfie')}),
    )

    readonly_fields = ['display_photos']

    def display_id_status(self, obj):
        if obj.is_verified:
            return format_html('<span style="color: green; font-weight: bold;">تم التحقق</span>')
        return format_html('<span style="color: red;">قيد الانتظار</span>')
    display_id_status.short_description = "حالة الهوية"

    def display_photos(self, obj):
        html = ""
        if obj.id_front:
            html += f'<div><p>الهوية أمامية:</p><img src="{obj.id_front.url}" width="300" /></div>'
        if obj.id_back:
            html += f'<div><p>الهوية خلفية:</p><img src="{obj.id_back.url}" width="300" /></div>'
        if obj.selfie:
            html += f'<div><p>سيلفي التحقق:</p><img src="{obj.selfie.url}" width="300" /></div>'
        return format_html(html) if html else "لا توجد صور"
    display_photos.short_description = "معاينة الوثائق"

admin.site.register(User, CustomUserAdmin)

@admin.register(BroadcastNotification)
class BroadcastNotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_at']
    search_fields = ['title', 'message']

    def save_model(self, request, obj, form, change):
        # Save the broadcast record first
        super().save_model(request, obj, form, change)
        
        # Only broadcast on creation, not on edit
        if not change:
            users = User.objects.filter(is_active=True)
            batch_size = 500
            notifications = []
            
            for user in users:
                notifications.append(Notification(
                    user=user,
                    title=obj.title,
                    message=obj.message
                ))
                
                # Bulk create in batches to avoid memory issues
                if len(notifications) >= batch_size:
                    Notification.objects.bulk_create(notifications)
                    notifications = []
                    
            if notifications:
                Notification.objects.bulk_create(notifications)
