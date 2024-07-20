# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Batches(models.Model):
    id = models.CharField(primary_key=True, max_length=150)
    institution = models.CharField(max_length=15)
    count = models.IntegerField()
    requesttime = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'batches'

    def __str__(self):
        return f"ID: {self.id} - Inst.: {self.institution}"


class Bins(models.Model):
    institution = models.CharField(primary_key=True, max_length=15)
    payarena = models.CharField(max_length=6)
    payattitude = models.CharField(max_length=6)
    nip = models.CharField(max_length=6)

    class Meta:
        managed = False
        db_table = 'bins'


class Institutions(models.Model):
    code = models.CharField(primary_key=True, max_length=200)
    name = models.CharField(unique=True, max_length=200)
    nibss_code = models.CharField(blank=True, null=True, max_length=200)
    alias = models.TextField(blank=True, null=True)  # This field type is a guess.
    routes = models.TextField(blank=True, null=True)  # This field type is a guess.
    supports_ir = models.BooleanField(blank=True, null=True)
    health_interval = models.IntegerField(blank=True, null=True)
    config = models.TextField(blank=True, null=True)  # This field type is a guess.
    is_enabled = models.BooleanField(blank=True, null=True)
    ir_intervals = models.TextField(blank=True, null=True)  # This field type is a guess.

    class Meta:
        managed = False
        db_table = 'institutions'

    def __str__(self):
        return f"{self.name} - {self.code}"


class Messages(models.Model):
    id = models.BigAutoField(primary_key=True)
    institution = models.CharField(max_length=15)
    txid = models.CharField(max_length=150, blank=True, null=True)
    direction = models.CharField(max_length=5, blank=True, null=True)
    endpoint = models.CharField(max_length=75, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    rawmsg = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=50, blank=True, null=True)
    occurred = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'messages'


class Stage(models.Model):
    institution = models.CharField(max_length=15, blank=True, null=True)
    txid = models.CharField(max_length=150, blank=True, null=True)
    sourcebank = models.CharField(max_length=15, blank=True, null=True)
    destbank = models.CharField(max_length=15, blank=True, null=True)
    accountno = models.CharField(max_length=20, blank=True, null=True)
    poolaccount = models.CharField(max_length=20, blank=True, null=True)
    amount = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    fee = models.DecimalField(max_digits=65535, decimal_places=65535, blank=True, null=True)
    remark = models.CharField(max_length=2000, blank=True, null=True)
    requestid = models.CharField(max_length=150, blank=True, null=True)
    requesttype = models.CharField(max_length=50, blank=True, null=True)
    requesttime = models.DateTimeField(blank=True, null=True)
    route = models.CharField(max_length=50, blank=True, null=True)
    routebin = models.CharField(max_length=10, blank=True, null=True)
    responsetime = models.DateTimeField(blank=True, null=True)
    statuscode = models.CharField(max_length=20, blank=True, null=True)
    statusmessage = models.CharField(max_length=200, blank=True, null=True)
    responseid = models.CharField(max_length=150, blank=True, null=True)
    rrn = models.CharField(max_length=20, blank=True, null=True)
    client = models.CharField(max_length=20, blank=True, null=True)
    requerycount = models.SmallIntegerField(blank=True, null=True)
    reversed = models.BooleanField(blank=True, null=True)
    reversible = models.BooleanField(blank=True, null=True)
    batchid = models.CharField(max_length=50, blank=True, null=True)
    approved = models.BooleanField(blank=True, null=True)
    beneficiary = models.CharField(max_length=60, blank=True, null=True)
    sender = models.CharField(max_length=60, blank=True, null=True)
    direction = models.CharField(max_length=10, blank=True, null=True)
    debitaccount = models.CharField(max_length=15, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'stage'


class Transfers(models.Model):
    institution = models.CharField(max_length=15)
    txid = models.CharField(primary_key=True, max_length=150)  # The composite primary key (txid, institution, direction) found, that is not supported. The first column is selected.
    sourcebank = models.CharField(max_length=15)
    destbank = models.CharField(max_length=15)
    accountno = models.CharField(max_length=20)
    poolaccount = models.CharField(max_length=20, blank=True, null=True)
    amount = models.DecimalField(max_digits=65535, decimal_places=65535)
    fee = models.DecimalField(max_digits=65535, decimal_places=65535)
    remark = models.CharField(max_length=2000, blank=True, null=True)
    requestid = models.CharField(max_length=150, blank=True, null=True)
    requesttype = models.CharField(max_length=50, blank=True, null=True)
    requesttime = models.DateTimeField(blank=True, null=True)
    route = models.CharField(max_length=50, blank=True, null=True)
    routebin = models.CharField(max_length=10, blank=True, null=True)
    responsetime = models.DateTimeField(blank=True, null=True)
    statuscode = models.CharField(max_length=20, blank=True, null=True)
    statusmessage = models.CharField(max_length=200, blank=True, null=True)
    responseid = models.CharField(max_length=150, blank=True, null=True)
    rrn = models.CharField(max_length=150, blank=True, null=True)
    client = models.CharField(max_length=20, blank=True, null=True)
    requerycount = models.SmallIntegerField(blank=True, null=True)
    reversed = models.BooleanField(blank=True, null=True)
    reversible = models.BooleanField(blank=True, null=True)
    batchid = models.CharField(max_length=50, blank=True, null=True)
    approved = models.BooleanField(blank=True, null=True)
    beneficiary = models.CharField(max_length=200, blank=True, null=True)
    sender = models.CharField(max_length=100, blank=True, null=True)
    direction = models.CharField(max_length=10)
    debitaccount = models.CharField(max_length=15, blank=True, null=True)
    reference = models.CharField(max_length=30, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'transfers'
        unique_together = (('txid', 'institution', 'direction'),)

    def __str__(self):
        return f"{self.txid}: source - {self.sourcebank}, dest: {self.destbank}"
