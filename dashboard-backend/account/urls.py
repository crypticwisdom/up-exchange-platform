from django.urls import path
from . import views

app_name = "account"

urlpatterns = [
    path('create-user/', views.CreateAdminAPIView.as_view(), name="create-user"),
    path('login/', views.LoginAPIView.as_view(), name="login"),

    path('confirm-otp', views.ConfirmOTPView.as_view(), name="confirm-otp"),
    path('change-password/', views.ChangePasswordView.as_view(), name="change-password"),
    path('forgot-password/', views.ForgotPasswordView.as_view(), name="forgot-password"),

    path('institution/', views.InstitutionAPIView.as_view(), name="institution"),
    path('institution/image/', views.UploadInstitutionImage.as_view(), name="institution-image"),
    path('institution/<int:pk>/', views.InstitutionAPIView.as_view(), name="institution"),
    path('institution-dashboard/<int:pk>/', views.InstitutionDashboardAPIView.as_view(), name="institution-dashboard"),

    # Create Instition from file
    path('update-organisation/', views.UpdateInstitutionFromFileView.as_view(), name="update-institution"),
    path('admin/', views.AdminListAPIView.as_view(), name="list-admin"),
    path('admin/<int:pk>/', views.AdminListAPIView.as_view(), name="delete-admin"),

    path('email-trigger/', views.EmailTriggerAPIView.as_view(), name="email-trigger"),
]

