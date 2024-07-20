# Generated by Django 2.2 on 2023-05-12 09:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_auto_20230511_1523'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='metrics',
            field=models.CharField(blank=True, choices=[('indicator', 'indicator'), ('transactionReport', 'Transaction Report'), ('transactionPerformance', 'Transaction Performance'), ('institutionPerformance', 'Institution Performance'), ('approvalRate', 'Approval Rate')], max_length=200, null=True),
        ),
    ]
