import ast
import datetime
import json
import secrets

from django.utils import timezone
from threading import Thread
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404

# from api.models import Institutions
from core.modules.email_template import account_opening_email, send_token_to_email, send_forgot_password_token_to_email
from core.modules.exceptions import InvalidRequestException, raise_serializer_error_msg
from core.modules.utils import generate_random_password, encrypt_text, format_phone_number, generate_random_otp, \
    get_next_minute, api_response, log_request, decrypt_text, password_checker

from .choices import INSTITUTION_TYPE_CHOICES, ROLE_CHOICES
from .models import Profile, Organisation, OrganisationImage, EmailTrigger
from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password, check_password


class OrganisationSerializerOut(serializers.ModelSerializer):
    institutionType = serializers.CharField(source="institution_type")
    createdOn = serializers.DateTimeField(source="created_on")
    updatedOn = serializers.DateTimeField(source="updated_on")
    supportEmails = serializers.SerializerMethodField()
    administrators = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()
    emailTrigger = serializers.SerializerMethodField()

    def get_emailTrigger(self, obj):
        trigger = None
        if EmailTrigger.objects.filter(institution=obj).exists():
            trigger = EmailTriggerSerializerOut(EmailTrigger.objects.filter(institution=obj).last()).data
        return trigger

    def get_logo(self, obj):
        if obj.logo:
            request = self.context.get("request")
            image = dict()
            image["id"] = obj.logo.id
            # image["url"] = request.build_absolute_uri(obj.logo.image.url)
            image["url"] = f"{request.scheme}://{request.get_host()}/{obj.logo.image.url}"
            return image
        return None

    def get_administrators(self, obj):
        inst_admin = Profile.objects.filter(role__in=["bankAdmin", "nonBankAdmin"], organisation=obj)
        return [
            {"id": admin.user_id, "name": admin.user.get_full_name(), "phoneNumber": admin.phone_number,
             "role": admin.role, "email": admin.user.email, "dateCreated": admin.created_on,
             "metrics": ast.literal_eval(str(admin.metrics))} for admin in inst_admin
        ]

    def get_users(self, obj):
        inst_users = Profile.objects.filter(
            role__in=["bankUser1", "nonBankUser1", "bankUser2", "nonBankUser2"], organisation=obj)
        return [
            {"id": admin.user_id, "name": admin.user.get_full_name(), "phoneNumber": admin.phone_number,
             "role": admin.role, "email": admin.user.email, "dateCreated": admin.created_on,
             "metrics": ast.literal_eval(str(admin.metrics))} for admin in inst_users
        ]

    def get_supportEmails(self, obj):
        if obj.support_emails:
            return ast.literal_eval(str(obj.support_emails))
        return obj.support_emails

    class Meta:
        model = Organisation
        exclude = ["updated_on", "institution_type", "created_on", "support_emails"]


class ProfileSeriializerOut(serializers.ModelSerializer):
    phoneNumber = serializers.CharField(source="phone_number")
    passwordChanged = serializers.BooleanField(source="password_changed")
    updatedOn = serializers.CharField(source="updated_on")
    createdBy = serializers.CharField(source="created_by")
    createdOn = serializers.CharField(source="created_on")
    deletedOn = serializers.CharField(source="deleted_on")
    deletedBy = serializers.CharField(source="deleted_by")
    institution = serializers.SerializerMethodField()
    metrics = serializers.SerializerMethodField()

    def get_metrics(self, obj):
        if obj.metrics:
            return ast.literal_eval(str(obj.metrics))
        return obj.metrics

    def get_institution(self, obj):
        if obj.organisation:
            return OrganisationSerializerOut(obj.organisation, context={"request": self.context.get("request")}).data
        return None

    class Meta:
        model = Profile
        exclude = [
            "id", "created_on", "otp", "otp_expiry", "user", "phone_number", "password_changed", "updated_on",
            "created_by", "organisation", "deleted_on", "deleted_by"
        ]


class UserSerializerOut(serializers.ModelSerializer):
    firstName = serializers.CharField(source="first_name")
    lastName = serializers.CharField(source="last_name")
    lastLogin = serializers.CharField(source="last_login")
    dateJoined = serializers.CharField(source="date_joined")
    userDetail = serializers.SerializerMethodField()

    def get_userDetail(self, obj):
        request = self.context.get("request")
        return ProfileSeriializerOut(obj.profile, context={"request": request}).data

    class Meta:
        model = User
        exclude = [
            "is_staff", "is_active", "is_superuser", "password", "first_name", "last_name", "groups",
            "user_permissions", "last_login", "date_joined"
        ]


class ProfileSerializerIn(serializers.Serializer):
    current_user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    firstName = serializers.CharField()
    lastName = serializers.CharField()
    email = serializers.EmailField()
    phoneNo = serializers.CharField(max_length=15)
    role = serializers.ChoiceField(choices=ROLE_CHOICES)
    institutionId = serializers.CharField(required=False)
    metrics = serializers.ListSerializer(child=serializers.CharField())

    def create(self, validated_data):
        auth_user = validated_data.get('current_user')
        first_name = validated_data.get("firstName")
        last_name = validated_data.get("lastName")
        email = validated_data.get("email")
        phone_no = validated_data.get("phoneNo")
        role = validated_data.get("role")
        institution_id = validated_data.get("institutionId")
        metrics = validated_data.get("metrics")

        auth_profile = Profile.objects.get(user=auth_user)
        non_admins = ["bankUser1", "bankUser2", "nonBankUser1", "nonBankUser2"]
        non_administrator = ["bankAdmin", "nonBankAdmin", "bankUser1", "bankUser2", "nonBankUser1", "nonBankUser2"]

        mt = ["sitePerformance", "transactionReport", "transactionPerformance", "institutionPerformance",
              "transactionCountAmount", "todayTransaction", "institutionUserAdminCount"]

        mo = False
        if any(item not in mt for item in metrics):
            mo = True

        if mo:
            response = api_response(message="Invalid dashboard metric selected for user", status=False)
            raise InvalidRequestException(response)

        if auth_profile.organisation is not None:
            org = auth_profile.organisation

        elif role in non_administrator:
            if not institution_id:
                response = api_response(message="Institution code is required", status=False)
                raise InvalidRequestException(response)
            try:
                org = Organisation.objects.get(code=institution_id)
            except Organisation.DoesNotExist:
                response = api_response(message="Selected Institution is not available/found", status=False)
                raise InvalidRequestException(response)

        elif auth_profile.role in non_admins:
            response = api_response(message="You are not permitted to perform this action", status=False)
            raise InvalidRequestException(response)

        else:
            org = None

        # Reformat Phone Number
        phone_number = format_phone_number(phone_no)

        bank_roles = ["bankAdmin", "bankUser1", "bankUser2"]
        non_bank_role = ["nonBankAdmin", "nonBankUser1", "nonBankUser2"]

        if org:
            # Check Institution Type
            inst_type = org.institution_type
            if inst_type == "bank" and role not in bank_roles:
                response = api_response(message="Invalid role selected for institution", status=False)
                raise InvalidRequestException(response)
            if inst_type == "nonBank" and role not in non_bank_role:
                response = api_response(message="Invalid role selected for institution", status=False)
                raise InvalidRequestException(response)

            # Check email belong to institution domain
            if not org.domain:
                response = api_response(message="Domain not configured for selected institution", status=False)
                raise InvalidRequestException(response)
            if not str(email).endswith(org.domain):
                response = api_response(message="Email provided does not belong to institution domain", status=False)
                raise InvalidRequestException(response)

        # Check if user with same email already exist
        if User.objects.filter(email__iexact=email).exists():
            response = api_response(message="User with this email already exist", status=False)
            raise InvalidRequestException(response)

        # Generate random password
        random_password = generate_random_password()
        log_request(f"random password: {random_password}")

        # Create user
        user = User.objects.create(
            username=email, email=email, first_name=first_name, last_name=last_name,
            password=make_password(random_password)
        )

        # Create Profile
        user_profile = Profile.objects.create(user=user, phone_number=phone_number, role=role, created_by=auth_user)
        user_profile.organisation = org
        user_profile.metrics = metrics
        user_profile.save()

        # Send OTP to user
        Thread(target=account_opening_email, args=[user_profile, str(random_password)]).start()
        return UserSerializerOut(user, context={"request": self.context.get("request")}).data


class LoginSerializerIn(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def create(self, validated_data):
        email = validated_data.get("email")
        password = validated_data.get("password")
        user = authenticate(username=email, password=password)
        if not user:
            response = api_response(message="Invalid email or password", status=False, data={"passwordChanged": False})
            raise InvalidRequestException(response)

        user_profile = Profile.objects.get(user=user)
        if not user_profile.password_changed:
            # OTP Timeout
            expiry = get_next_minute(timezone.now(), 15)
            random_otp = generate_random_otp()
            encrypted_otp = encrypt_text(random_otp)
            user_profile.otp = encrypted_otp
            user_profile.otp_expiry = expiry
            user_profile.save()

            # Send OTP to user
            Thread(target=send_token_to_email, args=[user_profile]).start()
            response = api_response(message="Kindly change your default password", status=False,
                                    data={"passwordChanged": False, "userId": user.id})
            raise InvalidRequestException(response)

        return user


class OrganisationSerializerIn(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    domain = serializers.CharField()
    logo_id = serializers.IntegerField()
    supportEmails = serializers.ListField(child=serializers.EmailField())
    category = serializers.IntegerField(required=False)
    institutionType = serializers.ChoiceField(choices=INSTITUTION_TYPE_CHOICES)
    current_user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    def create(self, validated_data):
        auth_user = validated_data.get('current_user')
        code = validated_data.get("code")
        name = validated_data.get("name")
        domain = validated_data.get("domain")
        image = validated_data.get("logo_id")
        email = validated_data.get("supportEmails")
        category = validated_data.get("category", 0)
        institution_type = validated_data.get("institutionType")

        permitted_roles = ["chiefAdmin"]

        if not Profile.objects.filter(user=auth_user, role__in=permitted_roles).exists():
            response = api_response(message="Sorry, you are not permitted to perform this action", status=False)
            raise InvalidRequestException(response)

        domain_mismatch = False
        for item in email:
            if not str(item).endswith(domain):
                domain_mismatch = True

        if domain_mismatch:
            response = api_response(message="Support email(s) mismatch provided domain", status=False)
            raise InvalidRequestException(response)

        if Organisation.objects.filter(name__iexact=name).exists():
            response = api_response(message="Organisation with this name already exist", status=False)
            raise InvalidRequestException(response)

        if Organisation.objects.filter(code__iexact=code).exists():
            response = api_response(message="Organisation with this code already exist", status=False)
            raise InvalidRequestException(response)

        if not OrganisationImage.objects.filter(id=image).exists():
            response = api_response(message="Invalid image", status=False)
            raise InvalidRequestException(response)

        image_id = OrganisationImage.objects.get(id=image)

        # Create Organisation
        org = Organisation.objects.create(
            code=code, name=name, domain=domain, category=category, institution_type=institution_type,
            support_emails=email, logo=image_id
        )

        return OrganisationSerializerOut(org, context={"request": self.context.get("request")}).data


class OrganisationImageSerializerOut(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            # image = request.build_absolute_uri(obj.image.url)
            image = f"{request.scheme}://{request.get_host()}/{obj.image.url}"
            return image
        return None

    class Meta:
        model = OrganisationImage
        exclude = []


class ConfirmOTPSerializerIn(serializers.Serializer):
    """
        A reminder: request.data or request.GET is passed into this / other serializers with the 'data' kwarg.
        And automatically these serializers performs a check on the request against the fields to make sure the datas match
        the data types of the fields written / specified inside the serializer.

        e.g: request.GET.get('userId') must match the same property datatype as specified inside the serializer.
            and also match the name 'userId' = serializers.CharField().

        I can then grab serializer' validated datas inside the 'create', 'update' methods, with 'validated_data'.
        e.g: validated_data.get('userId').

    """
    userId = serializers.CharField()
    otp = serializers.CharField()

    def create(self, validated_data):
        userId = validated_data.get("userId")
        otp = validated_data.get("otp")
        user_profile = Profile.objects.filter(user__id=userId)

        if not user_profile.exists():
            response = api_response(message="'userId' does not match any user record", status=False)
            raise InvalidRequestException(response)

        user_profile = user_profile.last()

        if otp != decrypt_text(user_profile.otp):
            response = api_response(message="Invalid OTP", status=False)
            raise InvalidRequestException(response)

        # If OTP has expired
        if timezone.now() > user_profile.otp_expiry:
            response = api_response(message="OTP has expired kindly request for another OTP", status=False)
            raise InvalidRequestException(response)
        return {"userId": userId}


class ChangePasswordSerializerIn(serializers.Serializer):
    """Used for new user password reset and password forgot."""
    userId = serializers.CharField()
    oldPassword = serializers.CharField()
    newPassword = serializers.CharField()
    confirmPassword = serializers.CharField()

    def create(self, validated_data):
        userId = validated_data.get("userId")
        old_password = validated_data.get("oldPassword")
        new_password = validated_data.get("newPassword")
        confirm_password = validated_data.get("confirmPassword")

        user_query = User.objects.filter(id=userId)
        if not user_query.exists():
            response = api_response(message="'userId' does not match any user record", status=False)
            raise InvalidRequestException(response)

        user = user_query.last()

        if not check_password(password=old_password, encoded=user.password):
            response = api_response(message="Incorrect old password", status=False)
            raise InvalidRequestException(response)

        success, text = password_checker(password=new_password)
        if not success:
            response = api_response(message=text, status=False)
            raise InvalidRequestException(response)

        # Check if newPassword and confirmPassword match
        if new_password != confirm_password:
            response = api_response(message="New passwords does not match", status=False)
            raise InvalidRequestException(response)

        # Check if new and old passwords are the same
        if old_password == new_password:
            response = api_response(message="Old and New Passwords cannot be the same", status=False)
            raise InvalidRequestException(response)

        user.password = make_password(password=new_password)
        user.profile.password_changed = True
        user.save()
        user.profile.save()
        return "Password Reset Successful"


class ForgotPasswordSerializerIn(serializers.Serializer):
    email = serializers.EmailField(allow_null=True)

    def create(self, validated_data):
        email = validated_data.get("email")

        user_query = User.objects.filter(email=email)
        if not user_query.exists():
            raise InvalidRequestException(api_response(message="'email' does not exists in our database", status=False))

        user = user_query.last()
        user.profile.otp = secrets.token_urlsafe(15)
        user.profile.otp_expiry = timezone.now() + timezone.timedelta(minutes=10)
        user.profile.save()

        # Send email
        Thread(target=send_forgot_password_token_to_email, args=[user]).start()
        return "Forgot Password mail has been sent"


class ForgotPasswordOperationSerializerIn(serializers.Serializer):
    slug = serializers.CharField()
    password = serializers.CharField()
    confirmPassword = serializers.CharField()

    def create(self, validated_data):
        slug = validated_data.get('slug')
        password = validated_data.get('password')
        confirm_password = validated_data.get('confirmPassword')
        user_profile = Profile.objects.filter(otp=slug)

        if not user_profile.exists():
            raise InvalidRequestException(api_response(message="No profile matches the given slug", status=False))

        user_profile: Profile = user_profile.last()

        if timezone.now() > user_profile.otp_expiry:
            response = api_response(message="Forgot password link has expired, Please request for "
                                            "another link", status=False)
            user_profile.otp = None
            user_profile.save()
            raise InvalidRequestException(response)

        success, msg = password_checker(password=password)
        if not success:
            raise InvalidRequestException(api_response(message=msg, status=False))

        if password != confirm_password:
            raise InvalidRequestException(api_response(message="Passwords does not match", status=False))

        if check_password(password=password, encoded=user_profile.user.password):
            raise InvalidRequestException(
                api_response(message="New password must not be the same as your previous password", status=False))

        user_profile.user.password = make_password(password)
        user_profile.user.save()

        return "Password has be reset"


class EmailTriggerSerializerOut(serializers.ModelSerializer):
    approvalRate = serializers.IntegerField(source="approval_rate")
    nextJob = serializers.CharField(source="next_job")
    lastJobMessage = serializers.CharField(source="last_job_message")
    createdOn = serializers.DateTimeField(source="created_on")
    updatedOn = serializers.DateTimeField(source="update_on")

    class Meta:
        model = EmailTrigger
        exclude = ["approval_rate", "next_job", "last_job_message", "created_on", "update_on", "institution"]


class EmailTriggerSerializerIn(serializers.Serializer):
    institutionId = serializers.IntegerField()
    approvalRate = serializers.FloatField(max_value=100)
    duration = serializers.IntegerField()

    def create(self, validated_data):
        institution_id = validated_data.get("institutionId")
        approval_rate = validated_data.get("approvalRate")
        duration = validated_data.get("duration")

        org = get_object_or_404(Organisation, id=institution_id)
        to_start_at = timezone.now() + timezone.timedelta(seconds=duration)

        trigger, _ = EmailTrigger.objects.get_or_create(institution=org)
        trigger.approval_rate = approval_rate
        trigger.duration = duration
        trigger.next_job = to_start_at
        trigger.active = True
        trigger.save()

        return f"Successfully set email trigger for institution {org.name}"




