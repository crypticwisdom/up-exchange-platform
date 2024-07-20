from django.shortcuts import render
from django.conf import settings
from core.modules.utils import decrypt_text, send_email


def account_opening_email(profile, password):
    first_name = profile.user.first_name
    email = profile.user.email
    if not profile.user.first_name:
        first_name = "Exchange Admin"

    message = f"Dear {first_name}, <br><br>Welcome to <a href='{settings.FRONTEND_URL}' target='_blank'>" \
              f"PayArena Exchange Monitoring Dashboard.</a><br>Please see below, your username " \
              f"and password. You will be required to change your password on your first login <br><br>" \
              f"username: <strong>{email}</strong><br>password: <strong>{password}</strong>"
    subject = "Exchange Registration"
    contents = render(None, 'default_template.html', context={'message': message}).content.decode('utf-8')
    send_email(contents, email, subject)
    return True


def send_token_to_email(user_profile):
    first_name = user_profile.user.first_name
    if not user_profile.user.first_name:
        first_name = "Exchange Admin"
    email = user_profile.user.email
    decrypted_token = decrypt_text(user_profile.otp)

    message = f"Dear {first_name}, <br><br>Kindly use the below One Time Token, to complete your action<br><br>" \
              f"OTP: <strong>{decrypted_token}</strong>"
    subject = "Exchange Registration"
    contents = render(None, 'default_template.html', context={'message': message}).content.decode('utf-8')
    send_email(contents, email, subject)
    return True


def send_forgot_password_token_to_email(user):
    first_name = user.first_name
    email = user.email
    url = f"{settings.FRONTEND_URL}/forgot-password?otp={user.profile.otp}"
    message = f"Dear {first_name}, <br><br>Kindly use the link below to Change your password<br><br>" \
              f"URL: <a href='{url}'>link</a>"
    subject = "Exchange Forgot Password"
    contents = render(None, 'default_template.html', context={'message': message}).content.decode('utf-8')
    send_email(contents, email, subject)
    return True


def site_performance_alert(email, performance, value, inst_name, second):
    name = f"{inst_name} System Administrator"
    metric = "response time"
    if performance == "approvalRate":
        metric = "approval rate"

    message = f"Dear {name}, <br><br>The {metric} of your inbound transfer service was " \
              f"<strong>{value}%</strong> within the last {second} seconds.<br>" \
              f"Kindly review the service for optimal performance<br><br>"
    subject = "PayArena Exchange Transfer Service Performance Monitor"
    contents = render(None, 'default_template.html', context={'message': message}).content.decode('utf-8')
    send_email(contents, email, subject)
    return True

