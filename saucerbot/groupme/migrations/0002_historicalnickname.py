# Generated by Django 2.0.6 on 2018-06-13 23:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groupme', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalNickname',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('groupme_id', models.CharField(max_length=32)),
                ('timestamp', models.DateTimeField()),
                ('nickname', models.CharField(max_length=256)),
            ],
        ),
    ]
