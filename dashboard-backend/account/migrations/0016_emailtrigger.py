# Generated by Django 2.2 on 2023-06-21 13:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0015_auto_20230531_1306'),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailTrigger',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('approval_rate', models.FloatField(default=50, help_text='Approval rate percentage')),
                ('duration', models.IntegerField(default=120, help_text='To run at per second(s) intervals')),
                ('next_job', models.DateTimeField(blank=True, null=True)),
                ('last_job_message', models.CharField(blank=True, max_length=200, null=True)),
                ('active', models.BooleanField(default=False)),
                ('created_on', models.DateTimeField(auto_now_add=True)),
                ('update_on', models.DateTimeField(auto_now=True)),
                ('institution', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Organisation')),
            ],
        ),
    ]
