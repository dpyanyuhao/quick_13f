# Generated by Django 4.2.4 on 2023-08-27 12:35

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FundInfo',
            fields=[
                ('cik', models.IntegerField(primary_key=True, serialize=False)),
                ('manager_name', models.CharField(blank=True, max_length=255, null=True)),
                ('city', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'fund_info',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='FundStats',
            fields=[
                ('id', models.CharField(blank=True, max_length=255, primary_key=True, serialize=False)),
                ('filing_period', models.DateField(db_index=True)),
                ('funds_deployed', models.BigIntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'fund_stats',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='PositionInfo',
            fields=[
                ('infotable_sk', models.IntegerField(primary_key=True, serialize=False)),
                ('accession_number', models.CharField(blank=True, max_length=255, null=True)),
                ('value', models.BigIntegerField(blank=True, null=True)),
                ('shares', models.BigIntegerField(blank=True, null=True)),
                ('filing_period', models.DateField(blank=True, db_index=True, null=True)),
            ],
            options={
                'db_table': 'position_info',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SecurityInfo',
            fields=[
                ('cusip', models.CharField(max_length=9, primary_key=True, serialize=False)),
                ('ticker', models.CharField(blank=True, max_length=255, null=True)),
                ('name', models.CharField(blank=True, max_length=255, null=True)),
                ('sector', models.CharField(blank=True, max_length=255, null=True)),
                ('asset_class', models.CharField(blank=True, max_length=255, null=True)),
                ('location', models.CharField(blank=True, max_length=255, null=True)),
                ('exchange', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'security_info',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='SecurityStats',
            fields=[
                ('id', models.CharField(blank=True, max_length=255, primary_key=True, serialize=False)),
                ('filing_period', models.DateField(db_index=True)),
                ('total_shares', models.BigIntegerField(blank=True, null=True)),
                ('total_value', models.BigIntegerField(blank=True, null=True)),
                ('total_count', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'security_stats',
                'managed': False,
            },
        ),
    ]