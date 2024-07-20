from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    path('transaction/', views.TransactionAPIView.as_view(), name="transaction"),
    path('transaction/<str:pk>/', views.TransactionAPIView.as_view(), name="transaction-detail"),

    path('dashboard/', views.AdminDashboardAPIView.as_view(), name="dashboard"),

    # CRON
    path('site-performance-cron', views.SitePerformanceCronView.as_view(), name="site-performance-cron"),

]

