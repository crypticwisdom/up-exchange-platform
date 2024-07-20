import ast
import base64
import calendar
import datetime
import decimal
import json
import logging
import re
import secrets
from operator import itemgetter
from threading import Thread

from django.db.models import Q, Avg, F, Sum, Count
from django.shortcuts import get_object_or_404, get_list_or_404
from django.utils import timezone
import requests
from cryptography.fernet import Fernet
from django.conf import settings
from django.utils.crypto import get_random_string
from dateutil.relativedelta import relativedelta

from account.models import Organisation, EmailTrigger
from api.models import Transfers


def log_request(*args):
    for arg in args:
        logging.info(arg)


def format_phone_number(phone_number):
    phone_number = f"0{phone_number[-10:]}"
    return phone_number


def encrypt_text(text: str):
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
    fernet = Fernet(key)
    secure = fernet.encrypt(f"{text}".encode())
    return secure.decode()


def decrypt_text(text: str):
    key = base64.urlsafe_b64encode(settings.SECRET_KEY.encode()[:32])
    fernet = Fernet(key)
    decrypt = fernet.decrypt(text.encode())
    return decrypt.decode()


def generate_random_password():
    return get_random_string(length=10)


def generate_random_otp():
    return get_random_string(length=6, allowed_chars="1234567890")


def get_previous_date(date, delta):
    previous_date = date - relativedelta(days=delta)
    return previous_date


def get_next_date(date, delta):
    next_date = date + relativedelta(days=delta)
    return next_date


def get_next_minute(date, delta):
    next_minute = date + relativedelta(minutes=delta)
    return next_minute


def get_previous_minute(date, delta):
    previous_minute = date - relativedelta(minutes=delta)
    return previous_minute


def get_previous_seconds(date, delta):
    # previous_seconds = date - datetime.timedelta(seconds=delta)
    previous_seconds = date - relativedelta(seconds=delta)
    return previous_seconds


def get_previous_hour(date, delta):
    previous_hour = date - relativedelta(hours=delta)
    return previous_hour


def get_day_start_and_end_datetime(date_time):
    day_start = date_time - relativedelta(day=0)
    # day_end = day_start + relativedelta(day=0)
    day_end = day_start + relativedelta(days=1)
    day_start = day_start.date()
    # day_start = datetime.datetime.combine(day_start.date(), datetime.time.min)
    # day_end = datetime.datetime.combine(day_end.date(), datetime.time.max)
    day_end = day_end.date()
    return day_start, day_end


def get_week_start_and_end_datetime(date_time):
    week_start = date_time - datetime.timedelta(days=date_time.weekday())
    week_end = week_start + datetime.timedelta(days=6)
    week_start = datetime.datetime.combine(week_start.date(), datetime.time.min)
    week_end = datetime.datetime.combine(week_end.date(), datetime.time.max)
    return week_start, week_end


def get_month_start_and_end_datetime(date_time):
    month_start = date_time.replace(day=1)
    month_end = month_start.replace(day=calendar.monthrange(month_start.year, month_start.month)[1])
    month_start = datetime.datetime.combine(month_start.date(), datetime.time.min)
    month_end = datetime.datetime.combine(month_end.date(), datetime.time.max)
    return month_start, month_end


def get_year_start_and_end_datetime(date_time):
    year_start = date_time.replace(day=1, month=1, year=date_time.year)
    year_end = date_time.replace(day=31, month=12, year=date_time.year)
    year_start = datetime.datetime.combine(year_start.date(), datetime.time.min)
    year_end = datetime.datetime.combine(year_end.date(), datetime.time.max)
    return year_start, year_end


def get_previous_month_date(date, delta):
    return date - relativedelta(months=delta)


def get_next_month_date(date, delta):
    return date + relativedelta(months=delta)


def send_email(content, email, subject):
    payload = json.dumps({"Message": content, "address": email, "Subject": subject})
    response = requests.request("POST", settings.EMAIL_URL, headers={'Content-Type': 'application/json'}, data=payload)
    # log_request(f"Email sent to: {email}")
    log_request(f"Sending email to: {email}, Response: {response.text}")
    return response.text


def incoming_request_checks(request, require_data_field: bool = True) -> tuple:
    try:
        x_api_key = request.headers.get('X-Api-Key', None) or request.META.get("HTTP_X_API_KEY", None)
        request_type = request.data.get('requestType', None)
        data = request.data.get('data', {})

        if not x_api_key:
            return False, "Missing or Incorrect Request-Header field 'X-Api-Key'"

        if x_api_key != settings.X_API_KEY:
            return False, "Invalid value for Request-Header field 'X-Api-Key'"

        if not request_type:
            return False, "'requestType' field is required"

        if request_type != "inbound":
            return False, "Invalid 'requestType' value"

        if require_data_field:
            if not data:
                return False, "'data' field was not passed or is empty. It is required to contain all request data"

        return True, data
    except (Exception,) as err:
        return False, f"{err}"


def get_incoming_request_checks(request) -> tuple:
    try:
        x_api_key = request.headers.get('X-Api-Key', None) or request.META.get("HTTP_X_API_KEY", None)

        if not x_api_key:
            return False, "Missing or Incorrect Request-Header field 'X-Api-Key'"

        if x_api_key != settings.X_API_KEY:
            return False, "Invalid value for Request-Header field 'X-Api-Key'"

        return True, ""
        # how do I handle requestType and also client ID e.g 'inbound', do I need to expect it as a query parameter.
    except (Exception,) as err:
        return False, f"{err}"


def api_response(message, status: bool, data=None, **kwargs) -> dict:
    if data is None:
        data = {}
    try:
        reference_id = secrets.token_hex(30)
        response = dict(requestTime=timezone.now(), requestType='outbound', referenceId=reference_id,
                        status=status, message=message, data=data, **kwargs)

        # if "accessToken" in data and 'refreshToken' in data:
        if "accessToken" in data:
            # Encrypting tokens to be
            response['data']['accessToken'] = encrypt_text(text=data['accessToken'])
            # response['data']['refreshToken'] = encrypt_text(text=data['refreshToken'])
            logging.info(msg=response)

            response['data']['accessToken'] = decrypt_text(text=data['accessToken'])
            # response['data']['refreshToken'] = encrypt_text(text=data['refreshToken'])

        else:
            logging.info(msg=response)

        return response
    except (Exception,) as err:
        return err


def password_checker(password: str):
    try:
        # Python program to check validation of password
        # Module of regular expression is used with search()

        flag = 0
        while True:
            if len(password) < 8:
                flag = -1
                break
            elif not re.search("[a-z]", password):
                flag = -1
                break
            elif not re.search("[A-Z]", password):
                flag = -1
                break
            elif not re.search("[0-9]", password):
                flag = -1
                break
            elif not re.search("[#!_@$-]", password):
                flag = -1
                break
            elif re.search("\s", password):
                flag = -1
                break
            else:
                flag = 0
                break

        if flag == 0:
            return True, "Valid Password"

        return False, "Password must contain uppercase, lowercase letters, '# ! - _ @ $' special characters " \
                      "and 8 or more characters"
    except (Exception,) as err:
        return False, f"{err}"


def validate_email(email):
    try:
        regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if re.fullmatch(regex, email):
            return True
        return False
    except (TypeError, Exception) as err:
        # Log error
        return False


def site_performance_indicator(**kwargs):
    date_from = kwargs.get("site_date_from")
    date_to = kwargs.get("site_date_to")
    institution_type = kwargs.get("institution_type")
    institution_id = kwargs.get("institution_id")
    report_type = kwargs.get("request_type")
    present_day = timezone.now() + relativedelta(hours=1)

    list_to_be_sorted = list()

    last_period = kwargs.get("last_period")

    if last_period:
        start_date = get_previous_seconds(date=present_day, delta=int(last_period))
        end_date = present_day
    elif date_from and date_to:
        start_date = date_from
        if date_to == str(present_day.date()):
            end_date = present_day
        else:
            end_date = date_to
    else:
        start_date = get_previous_seconds(date=present_day, delta=60)
        end_date = present_day

    log_request(f"\nDateFrom: {start_date}\nEndDate: {end_date}")

    all_institution = set(
        Transfers.objects.using("exchange").filter(requesttime__range=[start_date, end_date]).values_list(
            "destbank", flat=True).order_by("-amount"))

    if institution_type:
        # inst = Organisation.objects.filter(institution_type=institution_type, code__in=all_institution)[:10]
        inst = Organisation.objects.filter(institution_type=institution_type, code__in=all_institution)
    elif institution_id is not None:
        inst = Organisation.objects.filter(id=institution_id)
    else:
        # inst = Organisation.objects.filter(code__in=all_institution)[:10]
        inst = Organisation.objects.filter(code__in=all_institution)

    if report_type == "approvalRate":
        for item in inst:
            inst_code = str(item.code)
            total_out_going = Transfers.objects.using("exchange").filter(destbank=inst_code,
                                                                         requesttime__range=[start_date,
                                                                                             end_date]).count()
            success_out_going = Transfers.objects.using("exchange").filter(destbank=inst_code,
                                                                           requesttime__range=[start_date, end_date],
                                                                           statuscode="00").count()
            if total_out_going > 0:
                total = success_out_going / total_out_going
                result = total * 100
                data = dict()
                data["approvalRate"] = float(result).__ceil__()
                data["institution"] = item.name
                data["institutionId"] = item.id
                list_to_be_sorted.append(data)

        # response = sorted(list_to_be_sorted, key=lambda x: x['approvalRate'])[:10]
        # response = sorted(list_to_be_sorted, key=lambda x: x['institution'])[:10]
        response = sorted(list_to_be_sorted, key=lambda x: x['institution'])

    else:
        for item in inst:
            inst_code = str(item.code)
            result = Transfers.objects.using("exchange").filter(destbank=inst_code,
                                                                requesttime__range=[start_date, end_date]).aggregate(
                average_difference=Avg(F("responsetime") - F("requesttime")))["average_difference"] or "0"
            data = dict()
            if result == "0":
                num_seconds = 0
            else:
                num_seconds = result.total_seconds()
            data["averageSec"] = round(float(num_seconds), 1)
            data["institution"] = item.name
            data["institutionId"] = item.id
            list_to_be_sorted.append(data)

        # response = sorted(list_to_be_sorted, key=lambda x: x['averageSec'], reverse=True)[:10]
        # response = sorted(list_to_be_sorted, key=lambda x: x['institution'])[:10]
        response = sorted(list_to_be_sorted, key=lambda x: x['institution'])

    return response


def transaction_report(**kwargs):
    date_from = kwargs.get("date_from")
    date_to = kwargs.get("date_to")
    present_day = timezone.now() + relativedelta(hours=1)
    institution_id = kwargs.get("institution_id")
    institution_type = kwargs.get("institution_type")
    last_period = kwargs.get("last_period")
    response = list()

    query = Q()
    if last_period:
        start_date = get_previous_seconds(date=present_day, delta=int(last_period))
        end_date = present_day
        query &= Q(requesttime__range=[start_date, end_date])

    elif date_from and date_to:
        if date_to == str(present_day.date()):
            query &= Q(requesttime__range=[date_from, present_day])
        else:
            query &= Q(requesttime__range=[date_from, date_to])
    else:
        # get yesterday and current date
        yesterday = datetime.datetime.today().date() - datetime.timedelta(days=1)
        query &= Q(requesttime__range=[yesterday, present_day])

    trans = Transfers.objects.using("exchange").filter(query).order_by("-amount")
    # all_inst = set(trans.values_list("sourcebank", flat=True) | trans.values_list("destbank", flat=True))
    all_inst = set(value for pair in trans.values_list("sourcebank", "destbank") for value in pair)

    if institution_type:
        # inst_query = Q(sourcebank__in=all_inst) | Q(destbank__in=all_inst)
        inst = Organisation.objects.filter(institution_type=institution_type, code__in=all_inst)[:10]
    elif institution_id is not None:
        inst = Organisation.objects.filter(id=institution_id)
    else:
        inst = Organisation.objects.filter(code__in=all_inst)[:10]

    for item in inst:
        data = dict()
        inst_code = str(item.code)
        outbound = \
            Transfers.objects.using("exchange").filter(query, sourcebank=inst_code).count()
        inbound = \
            Transfers.objects.using("exchange").filter(query, destbank=inst_code).count()
        data["institution"] = item.name
        data["totalInbound"] = inbound
        data["totalOutbound"] = outbound
        response.append(data)

    response = sorted(response, key=lambda x: x['institution'])
    return response


def institution_performance(**kwargs):
    ip_period = kwargs.get("ip_period")
    institution_id = kwargs.get("institution_id")
    present_day = timezone.now() + relativedelta(hours=1)
    institution_type = kwargs.get("institution_type")

    end_date = present_day
    if ip_period == "weekly":
        start_date = get_previous_date(date=present_day, delta=7)
    else:
        start_date = present_day.date()

    response = list()

    tn = Transfers.objects.using("exchange").filter(requesttime__range=[start_date, end_date], approved=True,
                                                    requesttype="Credit").order_by("-amount")
    # all_inst = set(tn.values_list("sourcebank", "destbank", flat=True))
    all_inst = set(value for pair in tn.values_list("sourcebank", "destbank") for value in pair)

    if institution_type:
        # inst_query = Q(sourcebank__in=all_inst) | Q(destbank__in=all_inst)
        inst = Organisation.objects.filter(institution_type=institution_type, code__in=all_inst)

    elif institution_id is not None:
        inst = Organisation.objects.filter(id=institution_id)
    else:
        inst = Organisation.objects.filter(code__in=all_inst)

    for item in inst:
        inst_code = str(item.code)
        data = dict()
        outbound = Transfers.objects.using("exchange").filter(
            sourcebank=inst_code, requesttime__range=[start_date, end_date], approved=True,
            requesttype="Credit").aggregate(
            Sum("amount"))["amount__sum"] or 0
        inbound = Transfers.objects.using("exchange").filter(
            destbank=inst_code, requesttime__range=[start_date, end_date], approved=True,
            requesttype="Credit").aggregate(
            Sum("amount"))["amount__sum"] or 0
        data["institution"] = item.name
        data["inboundTransaction"] = inbound
        data["outboundTransaction"] = outbound
        response.append(data)

    response = sorted(response, key=itemgetter("inboundTransaction", "outboundTransaction"), reverse=True)

    return response


def transaction_performance(**kwargs):
    present_day = timezone.now() + relativedelta(hours=1)
    date_to = kwargs.get("date_to")
    institution_id = kwargs.get("institution_id")
    institution_type = kwargs.get("institution_type")
    date_from = kwargs.get("date_from")
    last_period = kwargs.get("last_period")
    direction = kwargs.get("direction")

    query = Q()

    if last_period:
        start_date = get_previous_seconds(date=present_day, delta=int(last_period))
        end_date = present_day
        query &= Q(requesttime__range=[start_date, end_date])

    elif date_from and date_to:
        if date_to == str(present_day.date()):
            query &= Q(requesttime__range=[date_from, present_day])
        else:
            query &= Q(requesttime__range=[date_from, date_to])

    response = []

    tran = Transfers.objects.using("exchange").filter(query).order_by("-amount")
    # all_inst = set(tran.values_list("sourcebank", "destbank", flat=True))
    all_inst = set(value for pair in tran.values_list("sourcebank", "destbank") for value in pair)

    if institution_type:
        # inst_query = Q(sourcebank__in=all_inst) | Q(destbank__in=all_inst)
        inst = Organisation.objects.filter(institution_type=institution_type, code__in=all_inst)

    elif institution_id is not None:
        inst = Organisation.objects.filter(id=institution_id)
    else:
        inst = Organisation.objects.filter(code__in=all_inst)

    for item in inst:
        inst_code = str(item.code)
        data = dict()
        data["institution"] = item.name
        if direction == "outbound":
            t_query = Transfers.objects.using("exchange").filter(query, sourcebank=inst_code)
        else:
            t_query = Transfers.objects.using("exchange").filter(query, destbank=inst_code)

        total = t_query.count()
        pending = t_query.filter(statuscode="05").count()
        success = t_query.filter(statuscode="00").count()
        failed = t_query.filter(statuscode="03").count()

        data["total"] = total
        data["pending"] = pending
        data["success"] = success
        data["failed"] = failed
        response.append(data)

    response = [item for item in response if item['total'] != 0]  # POP result with zero (0) total
    response = sorted(response, key=lambda x: x['institution'])

    return response


def institution_dashboard_data(institution, direction):
    today = timezone.datetime.today().date()
    tomorrow = timezone.datetime.today().date() + relativedelta(days=1)

    # total_transaction, total_transaction_inbound, total transaction outbound, total transaction count,
    # total successful transaction, total pending transaction, total failed transaction, total approved transaction,
    # total institution admin, total institution admin 1, total institution admin 2, total institution user,
    # total institution user 1, total institution user 2
    inst_code = str(institution.code)
    query = Q(requesttime__range=[today, tomorrow])

    if institution.institution_type == "nonBank":
        query &= Q(requesttype="Credit")

    if direction == "inbound":
        query &= Q(destbank=inst_code)

    if direction == "outbound":
        query &= Q(sourcebank=inst_code)

    query_results = Transfers.objects.using("exchange").filter(query)

    data = dict()
    data["totalTransactionAmount"] = query_results.aggregate(total=Sum("amount")).get("total", 0) or 0
    data["totalTransactionCount"] = query_results.count()

    status_query = query_results.values("statuscode").annotate(total_amount=Sum("amount"), count=Count("txid"))

    status_dict = {status["statuscode"]: (status["total_amount"] or 0, status["count"]) for status in status_query}

    data["totalSuccessTransactionAmount"], data["totalSuccessTransactionCount"] = status_dict.get("00", (0, 0))
    data["totalFailedTransactionAmount"], data["totalFailedTransactionCount"] = status_dict.get("03", (0, 0))
    data["totalPendingTransactionAmount"], data["totalPendingTransactionCount"] = status_dict.get("05", (0, 0))

    data["totalApprovedTransactionAmount"] = query_results.filter(approved=True).aggregate(total=Sum("amount")).get(
        "total", 0) or 0
    data["totalApprovedTransactionCount"] = query_results.filter(approved=True).count()

    return data


def dashboard_transaction_data(institution):
    inst_code = institution.code
    trans = dict()
    daily = []
    weekly = []
    monthly = []
    yearly = []
    query = Q(sourcebank=inst_code) | Q(destbank=inst_code)

    if institution.institution_type == "nonBank":
        query &= Q(requesttype="Credit")

    current_date = datetime.datetime.now()
    for delta in range(6, -1, -1):
        week_date = current_date - relativedelta(days=delta)
        week_start, week_end = get_day_start_and_end_datetime(week_date)
        # week_start, week_end = get_week_start_and_end_datetime(week_date)

        week_total_trans = month_total_trans = year_total_trans = week_count = month_count = year_count = 0
        # week_date = current_date - relativedelta(weeks=delta)
        # week_start, week_end = get_week_start_and_end_datetime(week_date)
        # month_date = current_date - relativedelta(months=delta)
        # year_date = current_date - relativedelta(years=delta)
        # month_start, month_end = get_month_start_and_end_datetime(month_date)
        # year_start, year_end = get_year_start_and_end_datetime(year_date)
        # print(year_start, year_end)
        total_trans = Transfers.objects.using("exchange").filter(query, requesttime__range=[week_start, week_end])

        if total_trans:
            week_total_trans = total_trans.aggregate(Sum("amount"))["amount__sum"] or 0
            week_count = total_trans.count()
        weekly.append({"week": f'{week_start.strftime("%d %b")}', "amount": week_total_trans, "count": week_count})
        # total_trans = Transfers.objects.using("exchange").filter(query, requesttime__range=[month_start, month_end])

        # if total_trans:
        #     month_total_trans = total_trans.aggregate(Sum("amount"))["amount__sum"] or 0
        #     month_count = total_trans.count()
        # monthly.append({"month": month_start.strftime("%b"), "amount": month_total_trans, "count": month_count})
        # total_trans = Transfers.objects.using("exchange").filter(query, requesttime__range=[year_start, year_end])
        # if total_trans:
        #     year_total_trans = total_trans.aggregate(Sum("amount"))["amount__sum"] or 0
        #     year_count = total_trans.count()
        # yearly.append({"year": year_start.strftime("%Y"), "amount": year_total_trans, "count": year_count})
    trans['weekly'] = weekly
    # trans['monthly'] = monthly
    # trans['yearly'] = yearly
    return trans


# def get_today_transaction_counts(query, start_date, end_date):
def get_today_transaction_counts(query):
    start_date = timezone.now().date()
    end_date = str(timezone.now().date() + relativedelta(days=1))

    data = dict()

    status = Q(statuscode="00") | Q(statuscode="03") | Q(statuscode="05")

    total_transaction = \
    Transfers.objects.using("exchange").filter(query, requesttime__range=[start_date, end_date]).aggregate(
        Sum("amount"))["amount__sum"] or 0

    success_transaction_amount = \
        Transfers.objects.using("exchange").filter(query, statuscode="00",
                                                   requesttime__range=[start_date, end_date]).aggregate(Sum("amount"))[
            "amount__sum"] or 0

    failed_transaction_amount = \
        Transfers.objects.using("exchange").filter(query, statuscode="03",
                                                   requesttime__range=[start_date, end_date]).aggregate(Sum("amount"))[
            "amount__sum"] or 0
    pending_transaction_amount = \
        Transfers.objects.using("exchange").filter(query, statuscode="05",
                                                   requesttime__range=[start_date, end_date]).aggregate(Sum("amount"))[
            "amount__sum"] or 0

    null_transaction_amount = \
        Transfers.objects.using("exchange").filter(query, requesttime__range=[start_date, end_date]).exclude(
            status).aggregate(Sum("amount"))[
            "amount__sum"] or 0

    status_counts = Transfers.objects.using('exchange').filter(
        query, requesttime__range=[start_date, end_date]).values('statuscode').annotate(count=Count('statuscode'))

    today_transaction_count = sum(status_counts.values_list('count', flat=True))
    today_success_tran_count = sum(status_counts.filter(statuscode='00').values_list('count', flat=True))
    today_pending_tran_count = sum(status_counts.filter(statuscode='05').values_list('count', flat=True))
    today_failed_tran_count = sum(status_counts.filter(statuscode='03').values_list('count', flat=True))
    today_null_tran_count = sum(status_counts.exclude(status).values_list('count', flat=True))
    # today_null_tran_count = sum(status_counts.filter(statuscode='').values_list('count', flat=True))

    data["totalTransactionCount"] = today_transaction_count
    data["totalTransactionAmount"] = round(decimal.Decimal(total_transaction), 2)

    data["successTransactionCount"] = today_success_tran_count
    data["successTransactionAmount"] = round(decimal.Decimal(success_transaction_amount), 2)

    data["pendingTransactionCount"] = today_pending_tran_count + today_null_tran_count
    data["pendingTransactionAmount"] = round(decimal.Decimal(pending_transaction_amount + null_transaction_amount), 2)

    data["failedTransactionCount"] = today_failed_tran_count
    data["failedTransactionAmount"] = round(decimal.Decimal(failed_transaction_amount), 2)
    return data


def get_today_transaction_counts_new():
    from django.db import connections
    from decimal import Decimal

    start_date = str(timezone.now().date())
    end_date = str(timezone.now().date() + relativedelta(days=1))
    data = dict()

    # Total Transaction Count and Amount
    total_transaction_query = '''
        SELECT COALESCE(SUM(amount), 0) as total_amount
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(total_transaction_query, [start_date, end_date])
        total_transaction_amount = cursor.fetchone()[0] or 0

    # Success Transaction Count and Amount
    success_transaction_query = '''
        SELECT COALESCE(SUM(amount), 0) as success_amount
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s AND statuscode = '00'
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(success_transaction_query, [start_date, end_date])
        success_transaction_amount = cursor.fetchone()[0] or 0

    # Failed Transaction Count and Amount
    failed_transaction_query = '''
        SELECT COALESCE(SUM(amount), 0) as failed_amount
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s AND statuscode = '03'
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(failed_transaction_query, [start_date, end_date])
        failed_transaction_amount = cursor.fetchone()[0] or 0

    # Pending Transaction Count and Amount
    pending_transaction_query = '''
        SELECT COALESCE(SUM(amount), 0) as pending_amount
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s AND statuscode = '05'
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(pending_transaction_query, [start_date, end_date])
        pending_transaction_amount = cursor.fetchone()[0] or 0

    # Null Transaction Count and Amount
    null_transaction_query = '''
        SELECT COALESCE(SUM(amount), 0) as null_amount
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s AND statuscode = ''
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(null_transaction_query, [start_date, end_date])
        null_transaction_amount = cursor.fetchone()[0] or 0

    # Today's Transaction Count by Status Code
    today_transaction_query = '''
        SELECT statuscode, COUNT(statuscode) as count
        FROM transfers
        WHERE requesttime BETWEEN %s AND %s
        GROUP BY statuscode
    '''
    with connections["exchange"].cursor() as cursor:
        cursor.execute(today_transaction_query, [start_date, end_date])
        status_counts = cursor.fetchall()

    today_transaction_count = sum(count for _, count in status_counts)
    today_success_tran_count = sum(count for statuscode, count in status_counts if statuscode == '00')
    today_pending_tran_count = sum(count for statuscode, count in status_counts if statuscode == '05')
    today_failed_tran_count = sum(count for statuscode, count in status_counts if statuscode == '03')
    today_null_tran_count = sum(count for statuscode, count in status_counts if statuscode == '')

    data["totalTransactionCount"] = today_transaction_count
    data["totalTransactionAmount"] = round(Decimal(total_transaction_amount), 2)

    data["successTransactionCount"] = today_success_tran_count
    data["successTransactionAmount"] = round(Decimal(success_transaction_amount), 2)

    data["pendingTransactionCount"] = today_pending_tran_count + today_null_tran_count
    data["pendingTransactionAmount"] = round(Decimal(pending_transaction_amount + null_transaction_amount), 2)

    data["failedTransactionCount"] = today_failed_tran_count
    data["failedTransactionAmount"] = round(Decimal(failed_transaction_amount), 2)

    return data


def institution_site_performance_indicator(**kwargs):
    inst_code = kwargs.get("institution_code")
    last_period = kwargs.get("last_period")
    direction = kwargs.get("direction")
    report_type = kwargs.get("request_type")
    present_day = timezone.now() + relativedelta(hours=1)
    banks = kwargs.get("others")

    list_to_be_sorted = list()

    if last_period:
        start_date = get_previous_seconds(date=present_day, delta=int(last_period))
        end_date = present_day
    else:
        start_date = get_previous_seconds(date=present_day, delta=60)
        end_date = present_day

    if direction == "inbound":
        query = Q(requesttime__range=[start_date, end_date], destbank=inst_code)
        data = dict()
        result = Transfers.objects.using("exchange").filter(query).aggregate(
            average_difference=Avg(F("responsetime") - F("requesttime")))["average_difference"] or "0"
        item = get_object_or_404(Organisation, code=inst_code)

        if report_type == "indicator":
            if result == "0":
                num_seconds = 0
            else:
                num_seconds = result.total_seconds()
            data["averageSec"] = round(float(num_seconds), 1)
            data["institution"] = item.name
            list_to_be_sorted.append(data)
        else:
            success_out_going = Transfers.objects.using("exchange").filter(query, statuscode="00").count()
            total_out_going = Transfers.objects.using("exchange").filter(query).count()

            if total_out_going > 0:
                total = success_out_going / total_out_going
                result = total * 100
                data["approvalRate"] = float(result).__ceil__()
                data["institution"] = item.name
                list_to_be_sorted.append(data)

    else:
        query = Q(requesttime__range=[start_date, end_date], sourcebank=inst_code)
        all_institution = set(
            Transfers.objects.using("exchange").filter(query).values_list("destbank", flat=True).order_by("-amount"))

        inst = Organisation.objects.filter(code__in=all_institution)

        if report_type == "indicator":
            # for bank_code in banks:
            #     data = dict()
            # query &= Q(destbank=bank_code)
            # try:
            #     item_name = Organisation.objects.get(code=bank_code).name
            # except Organisation.DoesNotExist:
            #     item_name = ""
            # result = Transfers.objects.using("exchange").filter(query).aggregate(
            #     average_difference=Avg(F("responsetime") - F("requesttime")))["average_difference"] or "0"

            for item in inst:
                result = Transfers.objects.using("exchange").filter(query, destbank=str(item.code)).aggregate(
                    average_difference=Avg(F("responsetime") - F("requesttime")))["average_difference"] or "0"
                data = dict()

                if result == "0":
                    num_seconds = 0
                else:
                    num_seconds = result.total_seconds()
                data["averageSec"] = round(float(num_seconds), 1)
                data["institution"] = item.name
                list_to_be_sorted.append(data)
        else:
            for item in inst:
                total_out_going = Transfers.objects.using("exchange").filter(query, destbank=str(item.code)).count()
                success_out_going = Transfers.objects.using("exchange").filter(query, destbank=str(item.code),
                                                                               statuscode="00").count()
                if total_out_going > 0:
                    data = dict()
                    total = success_out_going / total_out_going
                    result = total * 100
                    data["approvalRate"] = float(result).__ceil__()
                    data["institution"] = item.name
                    list_to_be_sorted.append(data)

    return sorted(list_to_be_sorted, key=lambda x: x['institution'])


def institution_transaction_performance(institution, direction):
    inst_code = institution.code
    trans = dict()
    daily = []
    query = Q(destbank=inst_code)

    if direction == "outbound":
        query = Q(sourcebank=inst_code)

    if institution.institution_type == "nonBank":
        query &= Q(requesttype="Credit")

    current_date = timezone.datetime.now()
    for delta in range(6, -1, -1):
        day_date = current_date - relativedelta(days=delta)
        day_start, day_end = get_day_start_and_end_datetime(day_date)
        total_trans_amount = success_amount = pending_amount = failed_amount = 0

        total_trans = Transfers.objects.using("exchange").filter(query, requesttime__range=[day_start, day_end])

        if total_trans:
            total_trans_amount = \
            Transfers.objects.using("exchange").filter(query, requesttime__range=[day_start, day_end]).aggregate(
                Sum("amount"))[
                "amount__sum"] or 0
            success_amount = \
                Transfers.objects.using("exchange").filter(query, statuscode="00",
                                                           requesttime__range=[day_start, day_end]).aggregate(
                    Sum("amount"))[
                    "amount__sum"] or 0
            pending_amount = \
                Transfers.objects.using("exchange").filter(query, statuscode="05",
                                                           requesttime__range=[day_start, day_end]).aggregate(
                    Sum("amount"))[
                    "amount__sum"] or 0
            failed_amount = Transfers.objects.using("exchange").filter(query, statuscode="03",
                                                                       requesttime__range=[day_start,
                                                                                           day_end]).aggregate(
                Sum("amount"))[
                                "amount__sum"] or 0

        daily.append(
            {"day": f'{day_start.strftime("%d %b")}', "total": total_trans_amount, "success": success_amount,
             "pending": pending_amount, "failed": failed_amount}
        )
    trans['report'] = daily
    return trans


# CRON
def site_performance_cron():
    # try:
    from core.modules.email_template import site_performance_alert
    # Get All Email Trigger At this period
    current_date = timezone.now().date()
    year = current_date.year
    month = current_date.month
    day = current_date.day
    current_time = timezone.now().time()
    hour = current_time.hour
    minute = current_time.minute
    query = Q(
        next_job__year=year, next_job__month=month, next_job__day=day, next_job__hour=hour, next_job__minute=minute,
        active=True
    )
    all_trigger = [trigger for trigger in EmailTrigger.objects.filter(query)]
    log_request(f"All triggers: {all_trigger}")
    for trigger in all_trigger:
        try:
            sec = trigger.duration
            inst = trigger.institution
            inst_name = str(inst.name).capitalize()
            approval = trigger.approval_rate
            response = site_performance_indicator(request_type="approvalRate", institution_id=inst.id, last_period=sec)
            log_request(f"Performing email trigger for {inst.name} at {timezone.now()}")
            # update trigger
            value = 100
            if len(response) > 0:
                data = response[0]
                value = data["approvalRate"]
            trigger.next_job = timezone.now() + timezone.timedelta(seconds=sec)
            trigger.last_job_message = f"Last job completed at {timezone.now()}. Approval rate as at then was {value}%"
            trigger.save()

            # send warning if approval rate is less than threshold
            if value < approval:
                emails = ast.literal_eval(str(inst.support_emails))
                for email in emails:
                    log_request(f"Threshold is higher than expected, sending email to {email}")
                    # Thread(target=site_performance_alert, args=[email, "approvalRate", value, inst_name, sec]).start()
                    site_performance_alert(email, "approvalRate", value, inst_name, sec)
        except Exception as err:
            log_request(f"An error occurred. Error: {err}")

    return "Site Performance Cron ran successfully"
