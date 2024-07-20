from django.contrib import admin

from account.models import Profile, Organisation, OrganisationImage, EmailTrigger


class OrganisationModelAdmin(admin.ModelAdmin):
    search_fields = ["code", "name"]
    list_display = ["name", "code", "category"]
    list_filter = ["category", "institution_type"]


class EmailTriggerModelAdmin(admin.ModelAdmin):
    list_display = ["institution", "approval_rate", "duration", "active", "created_on", "next_job"]
    list_filter = ["active"]


admin.site.register(Profile)
admin.site.register(OrganisationImage)
admin.site.register(Organisation, OrganisationModelAdmin)
admin.site.register(EmailTrigger, EmailTriggerModelAdmin)

