from django.db import models
from django.contrib.auth.models import User
from .choices import ROLE_CHOICES, INSTITUTION_TYPE_CHOICES, DASHBOARD_METRICS_CHOICES


class OrganisationImage(models.Model):
    image = models.ImageField(upload_to="site-logos", null=True)

    def __str__(self):
        return f"{self.id} - {self.image}"


class Organisation(models.Model):
    code = models.CharField(max_length=200)
    name = models.CharField(unique=True, max_length=200)
    domain = models.CharField(max_length=300, blank=True, null=True)
    support_emails = models.TextField(null=True, blank=True)
    logo = models.ForeignKey(OrganisationImage, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.IntegerField(default=0)
    institution_type = models.CharField(max_length=100, choices=INSTITUTION_TYPE_CHOICES, default="nonBank")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}: {self.code}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=100, choices=ROLE_CHOICES)
    metrics = models.CharField(max_length=400, blank=True, null=True)
    organisation = models.ForeignKey(Organisation, on_delete=models.SET_NULL, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="profile_created_by")
    password_changed = models.BooleanField(default=False)
    otp = models.TextField(blank=True, null=True)
    otp_expiry = models.DateTimeField(blank=True, null=True)
    deleted_on = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="user_deleted_by")
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user}: {self.role} - {self.created_on}"


class EmailTrigger(models.Model):
    institution = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    approval_rate = models.FloatField(default=50, help_text="Approval rate percentage")
    duration = models.IntegerField(default=120, help_text="To run at per second(s) intervals")
    next_job = models.DateTimeField(null=True, blank=True)
    last_job_message = models.CharField(max_length=200, blank=True, null=True)
    active = models.BooleanField(default=False)
    created_on = models.DateTimeField(auto_now_add=True)
    update_on = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.institution_id}: {self.active} - {self.duration}"

