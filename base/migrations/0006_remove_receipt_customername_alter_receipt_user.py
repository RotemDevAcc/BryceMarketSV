# Generated by Django 4.2.7 on 2023-12-05 14:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0005_alter_receipt_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='receipt',
            name='customername',
        ),
        migrations.AlterField(
            model_name='receipt',
            name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
