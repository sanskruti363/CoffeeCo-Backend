# Generated by Django 4.2.9 on 2024-01-21 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_reset'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reset',
            name='email',
            field=models.CharField(max_length=255),
        ),
    ]
