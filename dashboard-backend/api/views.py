import csv
import datetime
import uuid

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, time
from rest_framework.response import Response
from rest_framework.views import APIView

from account.models import Profile
from api.models import Transfers
from core.modules.exceptions import InvalidRequestException
from core.modules.paginations import CustomPagination
from core.modules.serializers import TransactionSerializerOut, BankTransactionSerializerOut
from core.modules.utils import api_response, site_performance_indicator, institution_performance, \
    transaction_performance, get_day_start_and_end_datetime, \
    get_today_transaction_counts, site_performance_cron, log_request, transaction_report

admin_roles = ["chiefAdmin", "subAdmin1", "subAdmin2"]
bank_user_role = ["bankAdmin", "bankUser1", "bankUser2"]
non_bank_user_role = ["nonBankAdmin", "nonBankUser1", "nonBankUser2"]


class TransactionAPIView(APIView, CustomPagination):

    def get(self, request, pk=None):
        today = timezone.datetime.today().date()
        tomorrow = timezone.datetime.today().date() + relativedelta(days=1)

        search = request.GET.get("search")
        trans_status = request.GET.get("status")  # 00: success, 05: pending, 03: failed
        inst_code = request.GET.get("institutionCode")
        source = request.GET.get("sourceBank")
        dest = request.GET.get("destBank")
        request_date_from = request.GET.get("requestDateFrom")
        request_date_to = request.GET.get("requestDateTo")
        response_date_from = request.GET.get("responseDateFrom")
        response_date_to = request.GET.get("responseDateTo")
        request_type = request.GET.get("requestType")
        route = request.GET.get("route")
        amount_from = request.GET.get("amountFrom")
        amount_to = request.GET.get("amountTo")
        count_query_from = request.GET.get("requeryCountFrom")
        count_query_to = request.GET.get("requeryCountTo")
        download = request.GET.get("download")

        try:
            auth_user = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            raise InvalidRequestException(
                api_response(message="Profile not found for authenticated user", status=False))

        query = Q()

        if source:
            query &= Q(sourcebank=source)

        if dest:
            query &= Q(destbank=dest)

        if auth_user.role in bank_user_role:
            query &= Q(route__iexact="direct")

        if auth_user.role in non_bank_user_role:
            query &= Q(requesttype="Credit")

        if auth_user.role not in admin_roles:
            # GET Institution code
            org_code = str(auth_user.organisation.code)
            query &= Q(sourcebank=org_code) | Q(destbank=org_code)

        if auth_user.role in admin_roles and inst_code:
            org_code = inst_code
            query &= Q(sourcebank=org_code) | Q(destbank=org_code)

        date_range_fields = [
            ("requesttime", request_date_from, request_date_to),
            ("responsetime", response_date_from, response_date_to),
        ]

        for field, date_from, date_to in date_range_fields:
            if date_from and date_to:
                date_ = datetime.strptime(f"{date_to}", "%Y-%m-%d")
                date_to = date_ + relativedelta(days=1)
                date_f = datetime.strptime(f"{date_from}", "%Y-%m-%d")
                # date_from = date_f.replace(hour=0, minute=0, second=0)
                date_from = datetime.combine(date_f, time())
                date_to = datetime.combine(date_to, time())
                query &= Q(**{f"{field}__range": [date_from, date_to]})

        query_fields = {
            "requesttype__iexact": request_type,
            "route__iexact": route,
            "statuscode": trans_status,
        }

        for field, value in query_fields.items():
            if value:
                query &= Q(**{field: value})

        range_fields = [
            ("amount", amount_from, amount_to),
            ("requerycount", count_query_from, count_query_to),
        ]

        for field, value_from, value_to in range_fields:
            if value_from and value_to:
                query &= Q(**{f"{field}__range": [value_from, value_to]})

        search_fields = ["txid", "requestid", "statusmessage", "sourcebank", "destbank", "accountno", "responseid"]

        if search:
            for field in search_fields:
                if "," in search:
                    param = str(search).replace(" ", "").split(",")
                    query |= Q(**{field: param})
                else:
                    query |= Q(**{field: search})

        if pk:
            query &= Q(txid=pk)
            try:
                queryset = Transfers.objects.using("exchange").filter(query).order_by("-requesttime").last()
            except Transfers.DoesNotExist:
                raise InvalidRequestException(api_response(message="Requested resource not found", status=False))
            data_serializer = BankTransactionSerializerOut if auth_user.role in bank_user_role else TransactionSerializerOut
            data = data_serializer(queryset, context={"request": request}).data
        else:
            if not any([
                search, trans_status, inst_code, request_date_from, request_date_to, response_date_from,
                response_date_to, request_type, route, amount_from, amount_to, count_query_from, count_query_to,
                download
            ]):
                query &= Q(requesttime__range=[today, tomorrow])
            # if request_date_to and request_date_from:
            #     queryset = Transfers.objects.using("exchange").filter(query).extra(where=["DATE(requesttime) BETWEEN %s AND %s"], params=[request_date_from, request_date_to]).order_by("-requesttime")
            # elif response_date_to and response_date_from:
            #     queryset = Transfers.objects.using("exchange").filter(query).extra(where=["DATE(requesttime) BETWEEN %s AND %s"], params=[response_date_from, response_date_to]).order_by("-requesttime")
            # else:
            queryset = Transfers.objects.using("exchange").filter(query).order_by("-requesttime")
            transfer = self.paginate_queryset(queryset, request)
            data_serializer = BankTransactionSerializerOut if \
                auth_user.role in bank_user_role else TransactionSerializerOut
            serializer = data_serializer(transfer, many=True, context={"request": request}).data
            data = self.get_paginated_response(serializer).data

        if download == "true":
            fields = [
                'TXID', 'SOURCE_BANK', 'DESTINATION_BANK', 'ACCOUNT_NO', 'AMOUNT',
                'REMARK', 'REQUEST_ID',
                'REQUEST_TYPE', 'REQUEST_TIME', 'ROUTE', 'RESPONSE_TIME', 'STATUS_CODE', 'STATUS_MESSAGE',
                'RESPONSE_ID', 'RRN', 'REQUERY_COUNT', 'REVERSED',
                'BATCH_ID', 'APPROVED', 'BENEFICIARY',
                'SENDER', 'DEBIT_ACCOUNT', 'REFERENCE'
            ]
            t = datetime.now()
            file_path = f'{settings.BASE_DIR}'
            file_ = f'/static/transactions-report/{t.date()}{t.timestamp()}{str(uuid.uuid4().int)[:4]}.csv'
            file_name = f'{file_path}{file_}'
            link = f"{request.scheme}://{request.get_host()}{file_}"

            with open(file_name, 'w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fields)
                writer.writeheader()

                for trans in queryset:
                    data = {
                        "TXID": trans.txid,
                        "SOURCE_BANK": trans.sourcebank,
                        "DESTINATION_BANK": trans.destbank,
                        "ACCOUNT_NO": trans.accountno,
                        "AMOUNT": trans.amount,
                        "REMARK": trans.remark,
                        "REQUEST_ID": trans.requestid,
                        "REQUEST_TYPE": trans.requesttype,
                        "REQUEST_TIME": trans.requesttime,
                        "ROUTE": trans.route,
                        "RESPONSE_TIME": trans.responsetime,
                        "STATUS_CODE": trans.statuscode,
                        "STATUS_MESSAGE": trans.statusmessage,
                        "RESPONSE_ID": trans.responseid,
                        "RRN": trans.rrn,
                        "REQUERY_COUNT": trans.requerycount,
                        "REVERSED": trans.reversed,
                        "BATCH_ID": trans.batchid,
                        "APPROVED": trans.approved,
                        "BENEFICIARY": trans.beneficiary,
                        "SENDER": trans.sender,
                        "DEBIT_ACCOUNT": trans.debitaccount,
                        "REFERENCE": trans.reference,
                    }
                    writer.writerow(data)

            data_ = {"downloadLink": link}
            return Response(api_response(message="CSV file generated", status=True, data=data_))

        return Response(api_response(message="Transfers retrieved", status=True, data=data))


class AdminDashboardAPIView(APIView):

    def get(self, request):
        inst_type = request.GET.get("institutionType", None)
        report_type = request.GET.get("reportType")  # indicator, transactionReport, transactionPerformance,
        # institutionPerformance, approvalRate

        date_from = request.GET.get("dateFrom", None)
        date_to = request.GET.get("dateTo", None)
        ind_last_period = request.GET.get("indicatorLastPeriod", None)  # seconds
        direction = request.GET.get("direction", "inbound")  # inbound, outbound

        ins_per_period = request.GET.get("ipDuration", None)  # daily, weekly, monthly

        user_profile = get_object_or_404(Profile, user=request.user)
        result = list()
        data = dict()
        inst_id = None
        start_, end_ = get_day_start_and_end_datetime(timezone.now())
        # today_date = timezone.datetime.now().date()

        # print(f"Today Transaction Date Range\nStartDate: {start_}\nEndDate: {end_}")
        # log_request(f"Today Transaction Date Range\nStartDate: {start_}\nEndDate: {end_}")

        t_query = Q()
        recent_transaction = TransactionSerializerOut(
            Transfers.objects.using("exchange").all().order_by("-requesttime")[:15], many=True).data
        if user_profile.role not in admin_roles:
            inst_code = str(user_profile.organisation.code)
            inst_id = user_profile.organisation.id
            query = Q(sourcebank=inst_code) | Q(destbank=inst_code)
            t_query &= Q(sourcebank=inst_code) | Q(destbank=inst_code)
            if user_profile.role in bank_user_role:
                query &= Q(route__iexact="direct")
            recent_transaction = BankTransactionSerializerOut(
                Transfers.objects.using("exchange").filter(query).order_by("-requesttime")[:15], many=True).data

        if report_type == "indicator":
            data["sitePerformanceIndicator"] = site_performance_indicator(
                institution_id=inst_id, site_date_from=date_from, site_date_to=date_to, institution_type=inst_type,
                last_period=ind_last_period
            )
            data["recentTransactions"] = recent_transaction
        elif report_type == "approvalRate":
            data["siteApprovalRate"] = site_performance_indicator(
                institution_id=inst_id, site_date_to=date_to, site_date_from=date_from, institution_type=inst_type,
                last_period=ind_last_period, request_type=report_type
            )
        elif report_type == "institutionPerformance":
            data["institutionPerformance"] = institution_performance(
                ip_period=ins_per_period, institution_type=inst_type, institution_id=inst_id
            )
        elif report_type == "transactionReport":
            data["transactionReport"] = transaction_report(
                date_from=date_from, date_to=date_to, institution_id=inst_id, institution_type=inst_type, last_period=ind_last_period,
            )
        elif report_type == "transactionPerformance":
            data["transactionPerformance"] = transaction_performance(
                date_from=date_from, date_to=date_to, institution_id=inst_id, institution_type=inst_type,
                last_period=ind_last_period, direction=direction
            )
        elif report_type == "todayStat":
            # from core.modules.utils import get_today_transaction_counts_new
            today_stat = get_today_transaction_counts(t_query)
            # today_stat = get_today_transaction_counts_new()
            data.update(today_stat)
        else:
            raise InvalidRequestException(api_response(message="Valid report type is required", status=False))

        result.append(data)
        return Response(api_response(message="Data retrieved", status=True, data=result))


# CRON
class SitePerformanceCronView(APIView):
    permission_classes = []

    def get(self, request):
        response = site_performance_cron()
        return Response({"detail": response})
