from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # Root
   from django.views.generic import RedirectView

path(
    '',
    RedirectView.as_view(
        pattern_name='dashboard',
        permanent=False
    ),
)
    # Auth
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('api/register/', views.register_api, name='register_api'),
    path(
    "api/login/",
    views.login_api,
    name="login_api"
),

    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Farmer database
    path('farmers/', views.farmer_list, name='farmer_list'),

    # Chat monitoring
    path('chat-monitoring/', views.chat_monitoring, name='chat_monitoring'),

    # Expert management
    path('experts/', views.expert_list, name='expert_list'),

    # Market rates admin
    path('market-rates/', views.market_rates, name='market_rates'),
    path('market-rates/create/', views.market_rate_create, name='market_rate_create'),
    path('market-rates/<int:pk>/delete/', views.market_rate_delete, name='market_rate_delete'),
    path('market-rates/<int:pk>/update/', views.market_rate_update, name='market_rate_update'),

    # Government schemes admin
    path('govt-schemes/', views.govt_schemes, name='govt_schemes'),
    path('govt-schemes/create/', views.scheme_create, name='scheme_create'),
    path('govt-schemes/<int:pk>/update/', views.scheme_update, name='scheme_update'),
    path('govt-schemes/<int:pk>/delete/', views.scheme_delete, name='scheme_delete'),
    path('govt-schemes/<int:pk>/status/', views.scheme_update_status, name='scheme_update_status'),

    # IoT admin + APIs
    path('iot/', views.iot_dashboard, name='iot_dashboard'),
    path('api/iot/ingest/', views.iot_ingest, name='iot_ingest'),
    path('api/iot/live/', views.iot_live_api, name='iot_live'),
    path('api/iot/history/', views.iot_history_api, name='iot_history'),
    path('api/sensor-data/', views.receive_sensor_data, name='sensor_api'),

    # Analytics & content
    path('analytics/', views.analytics, name='analytics'),
    path('content/', views.content_management, name='content'),
    path('settings/', views.settings_view, name='settings'),

    # Mobile / public JSON APIs
    path('api/market-rates/', views.market_rates_api, name='market_rates_api'),
    path('api/schemes/', views.schemes_api, name='schemes_api'),
    path('api/schemes/<int:pk>/', views.scheme_detail_api, name='scheme_detail_api'),
    path('api/chatbot/', views.chatbot_api, name='chatbot_api'),

    #notifications 

    path(
    "notifications/",
    views.notifications_api,
    name="notifications_api"),

path(
    "notifications/unread-count/",
    views.unread_notification_count,
    name="notification_count"),

path(
    "notifications/<int:notification_id>/read/",
    views.mark_notification_read,
    name="notification_read"),
]