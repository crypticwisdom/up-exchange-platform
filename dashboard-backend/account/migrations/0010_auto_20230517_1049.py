# Generated by Django 2.2 on 2023-05-17 09:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0009_auto_20230512_1120'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisation',
            name='support_emails',
            field=models.TextField(blank=True, null=True),
        ),
    ]
