from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.status import HTTP_400_BAD_REQUEST
from account.models import Organisation, Profile, OrganisationImage
from account.serializers import ProfileSerializerIn, LoginSerializerIn, UserSerializerOut, OrganisationSerializerOut, \
    OrganisationSerializerIn, ConfirmOTPSerializerIn, ChangePasswordSerializerIn, ForgotPasswordSerializerIn, \
    ForgotPasswordOperationSerializerIn, OrganisationImageSerializerOut, EmailTriggerSerializerIn
from api.models import Transfers

from core.modules.exceptions import raise_serializer_error_msg, InvalidRequestException
from core.modules.nip_list import nip_list_data
from core.modules.paginations import CustomPagination
from core.modules.serializers import TransactionSerializerOut, BankTransactionSerializerOut
from core.modules.utils import api_response, institution_dashboard_data, dashboard_transaction_data, \
    incoming_request_checks, get_incoming_request_checks, get_today_transaction_counts, \
    institution_site_performance_indicator, institution_transaction_performance

admin_roles = ["chiefAdmin", "subAdmin1", "subAdmin2"]
bank_user_role = ["bankAdmin", "bankUser1", "bankUser2"]
inst_admin_role = ["bankAdmin", "nonBankAdmin"]


# Done checks
class CreateAdminAPIView(APIView):
    permission_classes = []

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = ProfileSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message="Account created successfully", status=True, data=response))


# Done checks
class LoginAPIView(APIView):
    permission_classes = []

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = LoginSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        user = serializer.save()
        return Response(api_response(message="Login successful", status=True, data={
            "userData": UserSerializerOut(user, context={"request": request}).data,
            "accessToken": f"{RefreshToken.for_user(user).access_token}"}))


# Done checks
class InstitutionAPIView(APIView, CustomPagination):

    def get(self, request, pk=None):
        i_type = request.GET.get("institutionType")
        search = request.GET.get("search")
        query = Q(institution_type=i_type)

        if search:
            query &= Q(name__icontains=search) | Q(code__icontains=search) | Q(domain__icontains=search)

        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        try:
            auth_user = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            raise InvalidRequestException(api_response(message="Profile not found for user, please contact admin", status=False))

        if auth_user.role not in admin_roles:
            data = OrganisationSerializerOut(auth_user.organisation, context={"request": request}).data
            return Response(api_response(message="Request successful", status=True, data=data))

        if pk:
            try:
                org = Organisation.objects.get(id=pk)
            except Organisation.DoesNotExist:
                raise InvalidRequestException(api_response(message="Requested resource is not found", status=False))
            data = OrganisationSerializerOut(org, context={"request": request}).data
        else:
            obj = self.paginate_queryset(Organisation.objects.filter(query).order_by("name"), request)
            serializer = OrganisationSerializerOut(obj, many=True, context={"request": request}).data
            data = self.get_paginated_response(serializer).data

        return Response(api_response(message="Request successful", status=True, data=data))

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = OrganisationSerializerIn(data=data, context={"request": request})
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message="Institution created successfully", status=True, data=response))

    def put(self, request, pk):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        org = get_object_or_404(Organisation, id=pk)
        auth_user = get_object_or_404(Profile, user=request.user)

        if auth_user.role in admin_roles or (auth_user.organisation.id == org.id and auth_user.role in inst_admin_role):
            domain_name = data.get("domain")
            support_email = data.get("supportEmails")
            if domain_name:
                org.domain = domain_name
            if support_email:
                org.support_emails = support_email
            if auth_user.role == "chiefAdmin":
                name = data.get("name")
                inst_type = data.get("type")

                if inst_type not in ["bank", "nonBank"]:
                    raise InvalidRequestException(api_response(message="Invalid institution type", status=False))
                org.name = name
                org.institution_type = inst_type
            org.save()
            data = OrganisationSerializerOut(org, context={"request": request}).data
            return Response(api_response(message="Institution updated successfully", status=True, data=data))

        else:
            raise InvalidRequestException(api_response(message="You are not permitted to perform this action", status=False))


class UploadInstitutionImage(APIView):
    def post(self, request):
        image_file = request.data.get("image")
        image = OrganisationImage.objects.create(image=image_file)
        serializer = OrganisationImageSerializerOut(image, context={"request": request}).data
        return Response(api_response(message="Image uploaded", status=True, data=serializer))


# Done checks
class UpdateInstitutionFromFileView(APIView):
    permission_classes = []

    def get(self, request):
        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        banks = ["2", "7", "9"]
        for data in nip_list_data["FinancialInstitutionListRequest"]["Record"]:
            ins_code = data["InstitutionCode"]
            ins_name = data["InstitutionName"]
            ins_cat = data["Category"]

            if not Organisation.objects.filter(name__iexact=ins_name).exists():
                org = Organisation.objects.create(name=ins_name, code=ins_code, category=ins_cat)
                if ins_cat in banks:
                    org.institution_type = "bank"
                    org.save()
        return Response({"detail": "Institutions updated"})


# Done checks
class ConfirmOTPView(APIView):
    permission_classes = []

    def get(self, request):
        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = ConfirmOTPSerializerIn(data=request.GET)
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message="OTP has been verified successfully", data=response, status=True))


# Done checks
class ChangePasswordView(APIView):
    permission_classes = []

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = ChangePasswordSerializerIn(data=data)
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))


class ForgotPasswordView(APIView):
    """Used to request a forgot password mail and also forgot password operation"""
    permission_classes = []

    def get(self, request):
        """Used to request a forgot password mail"""
        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = ForgotPasswordSerializerIn(data=request.GET)
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))

    def post(self, request):
        """Used to perform forgot-password operation"""
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = ForgotPasswordOperationSerializerIn(data=data)
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))


# Done checks
class AdminListAPIView(APIView, CustomPagination):

    def get(self, request):
        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        admin_type = request.GET.get("adminType")
        search = request.GET.get("search")
        audit = request.GET.get("audit")

        query = Q(profile__role=admin_type)
        if search:
            query &= Q(first_name__icontains=search) | Q(last_name__icontains=search) | Q(email__icontains=search)
        valid_roles = ["chiefAdmin", "subAdmin1", "subAdmin2", "bankAdmin", "nonBankAdmin"]
        auth_user = get_object_or_404(Profile, user=request.user)
        role = auth_user.role
        if str(role) not in valid_roles:
            raise InvalidRequestException(api_response(message="Insufficient permission", status=False))
        queryset = self.paginate_queryset(User.objects.filter(query, is_active=True), request)
        if role == "chiefAdmin" and audit == "true":
            queryset = self.paginate_queryset(User.objects.filter(query, is_active=False), request)
        if role not in admin_roles:
            queryset = self.paginate_queryset(User.objects.filter(
                query, profile__organisation_id=auth_user.organisation_id, is_active=True), request)
        serializer = UserSerializerOut(queryset, many=True, context={"request": request}).data
        data = self.get_paginated_response(serializer).data
        return Response(api_response(message=f"{admin_type} retrieved successfully", status=True, data=data))

    def put(self, request, pk):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        phone_no = data.get("phoneNumber")
        role = data.get("role")
        metrics = data.get("metric")

        roles_for_admin = ["chiefAdmin", "subAdmin1", "subAdmin2", "bankAdmin", "nonBankAdmin"]

        auth_user = get_object_or_404(Profile, user=request.user)
        if str(auth_user.role) not in roles_for_admin:
            raise InvalidRequestException(api_response(message="Insufficient permission", status=False))
        acct_to_edit = get_object_or_404(User, id=pk)
        if str(auth_user.role) not in admin_roles:
            acct_to_edit = get_object_or_404(User, id=pk, profile__organisation_id=auth_user.organisation_id)

        mt = ["sitePerformance", "transactionReport", "transactionPerformance", "institutionPerformance",
              "transactionCountAmount", "todayTransaction", "institutionUserAdminCount"]

        mo = False
        if any(item not in mt for item in metrics):
            mo = True

        if mo:
            return Response(api_response(message="Invalid dashboard metric selected for user", status=False))

        acct = get_object_or_404(Profile, user=acct_to_edit)
        acct.phone_number = phone_no
        acct.role = role
        if metrics:
            acct.metrics = metrics
        acct.save()
        serializer = UserSerializerOut(acct_to_edit, context={"request": request}).data
        return Response(api_response(message=f"Account updated", status=True, data=serializer))

    def delete(self, request, pk):
        roles_for_admin = ["chiefAdmin", "subAdmin1", "subAdmin2", "bankAdmin", "nonBankAdmin"]
        auth_user = get_object_or_404(Profile, user=request.user)
        if str(auth_user.role) not in roles_for_admin:
            raise InvalidRequestException(api_response(message="Insufficient permission", status=False))
        acct_to_delete = get_object_or_404(User, id=pk)
        if str(auth_user.role) not in admin_roles:
            acct_to_delete = get_object_or_404(User, id=pk, profile__organisation_id=auth_user.organisation_id)
        acct_to_delete.is_active = False
        acct_to_delete.is_superuser = False
        acct_to_delete.is_staff = False
        acct_to_delete.save()
        # Update deleted user profile
        d_profile = get_object_or_404(Profile, user=acct_to_delete)
        d_profile.deleted_on = timezone.datetime.now()
        d_profile.deleted_by = request.user
        d_profile.save()
        return Response(api_response(message=f"User deleted successfully", status=True))


# Done checks
class InstitutionDashboardAPIView(APIView):
    def get(self, request, pk):
        status_, data_ = get_incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data_, status=False), status=HTTP_400_BAD_REQUEST)

        ind_last_period = request.GET.get("indicatorLastPeriod", None)  # seconds
        ind_banks_data = request.GET.get("indicatorBanks")  # 214,800,033
        outbound_bank = request.GET.get("outboundBank", "")
        report_type = request.GET.get("reportType")
        direction = request.GET.get("direction", "inbound")  # inbound, outbound

        ind_banks = str(ind_banks_data).split(",")

        institution = get_object_or_404(Organisation, id=pk)
        auth_user = get_object_or_404(Profile, user=request.user)
        response = list()
        data = dict()
        data["name"] = institution.name
        inst_code = str(institution.code)

        all_outbound_bank = list()

        a_query = Q(sourcebank=inst_code) | Q(destbank=inst_code)
        query = Q(destbank=inst_code)
        if direction == "outbound":
            query = Q(sourcebank=inst_code)

        if institution.institution_type == "nonBank":
            query &= Q(requesttype="Credit")
            a_query &= Q(requesttype="Credit")

        if outbound_bank:
            query &= Q(destbank=outbound_bank)

        recent_transaction = TransactionSerializerOut(
            Transfers.objects.using("exchange").filter(a_query).order_by("-requesttime")[:15], many=True).data

        if auth_user.role in bank_user_role:
            query &= Q(route__iexact="direct")
            recent_transaction = BankTransactionSerializerOut(
                Transfers.objects.using("exchange").filter(a_query).order_by("-requesttime")[:15], many=True).data

        if report_type == "indicator":
            data["sitePerformanceIndicator"] = institution_site_performance_indicator(
                institution_code=inst_code, last_period=ind_last_period, direction=direction, others=ind_banks,
                request_type=report_type
            )
            data["recentTransactions"] = recent_transaction
        elif report_type == "approvalRate":
            data["siteApprovalRate"] = institution_site_performance_indicator(
                institution_code=inst_code, last_period=ind_last_period, direction=direction, others=ind_banks
            )
        elif report_type == "adminUsers":
            inst_admin = Profile.objects.filter(role__in=["bankAdmin", "nonBankAdmin"],
                                                organisation=institution).count()
            inst_user_1 = Profile.objects.filter(role__in=["bankUser1", "nonBankUser1"],
                                                 organisation=institution).count()
            inst_user_2 = Profile.objects.filter(role__in=["bankUser2", "nonBankUser2"],
                                                 organisation=institution).count()

            data["institutionData"] = institution_dashboard_data(institution, direction)
            data["institutionData"]["institutionAdmin"] = inst_admin
            data["institutionData"]["institutionFirstUser"] = inst_user_1
            data["institutionData"]["institutionSecondUser"] = inst_user_2

        # elif report_type == "todayStat":
        #     today = timezone.datetime.today().date()
        #     tomorrow = timezone.datetime.today().date() + relativedelta(days=1)
        #     query &= Q(requesttime__range=[today, tomorrow])
        #     today_data = get_today_transaction_counts(query)
        #     data.update(today_data)
        elif report_type == "recentBanks":
            last_trans = Transfers.objects.using("exchange").filter(sourcebank=inst_code).order_by("-requesttime")[:15]
            if not ind_banks_data:
                ind_banks = list()
                for trans in last_trans:
                    if trans.destbank not in ind_banks:
                        try:
                            name = Organisation.objects.get(code=trans.destbank).name
                        except Organisation.DoesNotExist:
                            name = ""
                        ind_banks.append(trans.destbank)
                        all_outbound_bank.append({"code": trans.destbank, "name": name})

            data["recentBanks"] = all_outbound_bank

        elif report_type == "transaction":
            data["transaction"] = dashboard_transaction_data(institution)
        elif report_type == "transactionPerformance":
            data["transactionPerformance"] = institution_transaction_performance(institution, direction)
        else:
            raise InvalidRequestException(api_response(message="Valid report type is required", status=False))

        response.append(data)
        return Response(api_response(message="Data retrieved", status=True, data=response))


class EmailTriggerAPIView(APIView):
    permission_classes = []

    def post(self, request):
        status_, data = incoming_request_checks(request)
        if not status_:
            return Response(api_response(message=data, status=False), status=HTTP_400_BAD_REQUEST)

        serializer = EmailTriggerSerializerIn(data=data)
        serializer.is_valid() or raise_serializer_error_msg(errors=serializer.errors)
        response = serializer.save()
        return Response(api_response(message=response, status=True))

