from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import LoginView, RegisterView, UserListView, UserUpdateView, UserDeleteView, UserDetailView, KYCSubmissionView, AdminPasswordResetView, NotificationListView, MarkNotificationsReadView, BroadcastNotificationCreateView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user-update'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user-delete'),
    path('users/<int:pk>/reset-password/', AdminPasswordResetView.as_view(), name='user-reset-password'),
    path('me/', UserDetailView.as_view(), name='user-detail'),
    path('kyc/requests/', KYCSubmissionView.as_view(), name='kyc-submission'),
    path('notifications/', NotificationListView.as_view(), name='notifications-list'),
    path('notifications/mark_all_read/', MarkNotificationsReadView.as_view(), name='notifications-mark-read'),
    path('notifications/broadcast/', BroadcastNotificationCreateView.as_view(), name='broadcast-notification'),
    path('notifications/public-latest/', PublicBroadcastNotificationView.as_view(), name='public-latest-notification'),
]
