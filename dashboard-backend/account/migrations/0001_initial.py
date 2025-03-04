# Generated by Django 4.2 on 2023-04-20 11:30

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Organisation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=200)),
                ('name', models.CharField(unique=True)),
                ('nibss_code', models.CharField(blank=True, null=True)),
                ('alias', models.TextField(blank=True, null=True)),
                ('domain', models.CharField(blank=True, max_length=300, null=True)),
                ('institution_type', models.CharField(choices=[('bank', 'Bank'), ('nonBank', 'Non-Bank')], default='nonBank', max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone_number', models.CharField(max_length=20)),
                ('role', models.CharField(choices=[('chiefAdmin', 'Chief Admin'), ('subAdmin1', 'Sub Admin 1'), ('subAdmin2', 'Sub Admin 2'), ('bankAdmin', 'Bank Admin'), ('nonBankAdmin', 'Non-Bank Admin'), ('bankUser1', 'Bank User 1'), ('bankUser2', 'Bank User 2'), ('nonBankUser1', 'Non-Bank User 1'), ('nonBankUser2', 'Non-Bank User 2')], max_length=100)),
                ('password_changed', models.BooleanField(default=False)),
                ('otp', models.TextField(blank=True, null=True)),
                ('otp_expiry', models.DateTimeField(blank=True, null=True)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('updated_on', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='profile_created_by', to=settings.AUTH_USER_MODEL)),
                ('organisation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='account.organisation')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
