# Generated by Django 2.2.5 on 2019-09-08 03:13

import os

import django.db.models.manager
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groupme', '0003_rename_sauceruser'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalnickname',
            name='group_id',
            field=models.CharField(default=os.environ.get('GROUPME_GROUP_ID'), max_length=32),
            preserve_default=False,
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_token', models.CharField(max_length=64, unique=True)),
                ('user_id', models.CharField(max_length=32, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Bot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bots', to='groupme.User')),
                ('bot_id', models.CharField(max_length=32)),
                ('group_id', models.CharField(max_length=32)),
                ('name', models.CharField(max_length=64)),
                ('slug', models.SlugField(max_length=64, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Handler',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('handler_name', models.CharField(max_length=64)),
                ('bot', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='handlers', to='groupme.Bot')),
            ],
        ),
    ]