from rest_framework import serializers

from account.models import Organisation
from api.models import Transfers


class TransactionSerializerOut(serializers.ModelSerializer):
    sourcebank = serializers.SerializerMethodField()
    destbank = serializers.SerializerMethodField()
    amount = serializers.CharField()
    fee = serializers.CharField()

    def get_sourcebank(self, obj):
        if Organisation.objects.filter(code__iexact=obj.sourcebank).exists():
            source_inst_name = Organisation.objects.get(code__iexact=obj.sourcebank).name
            return source_inst_name
        return obj.sourcebank

    def get_destbank(self, obj):
        if Organisation.objects.filter(code__iexact=obj.destbank).exists():
            dest_inst_name = Organisation.objects.get(code__iexact=obj.destbank).name
            return dest_inst_name
        return obj.destbank

    class Meta:
        model = Transfers
        exclude = []


class BankTransactionSerializerOut(serializers.ModelSerializer):
    sourcebank = serializers.SerializerMethodField()
    destbank = serializers.SerializerMethodField()
    amount = serializers.CharField()

    def get_sourcebank(self, obj):
        if Organisation.objects.filter(code__iexact=obj.sourcebank).exists():
            source_inst_name = Organisation.objects.get(code__iexact=obj.sourcebank).name
            return source_inst_name
        return obj.sourcebank

    def get_destbank(self, obj):
        if Organisation.objects.filter(code__iexact=obj.destbank).exists():
            dest_inst_name = Organisation.objects.get(code__iexact=obj.destbank).name
            return dest_inst_name
        return obj.destbank

    class Meta:
        model = Transfers
        exclude = ["direction", "reversible", "routebin", "institution", "fee", "txid", "client", "route"]

# 8. Transaction: direction,reversible,routebin,institution,fee, txid, client, route columns should be
# removed from bank user's view
# 9. Only transactions where the route is not NIP should be displayed to bank users
