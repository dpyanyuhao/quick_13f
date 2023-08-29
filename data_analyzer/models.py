from django.db import models


class FundInfo(models.Model):
    cik = models.IntegerField(primary_key=True)
    manager_name = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fund_info'


class SecurityInfo(models.Model):
    cusip = models.CharField(primary_key=True, max_length=9)
    ticker = models.CharField(max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    sector = models.CharField(max_length=255, blank=True, null=True)
    asset_class = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    exchange = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'security_info'


class PositionInfo(models.Model):
    infotable_sk = models.IntegerField(primary_key=True)
    accession_number = models.CharField(max_length=255, blank=True, null=True)
    cusip = models.ForeignKey(SecurityInfo, models.DO_NOTHING, db_column='cusip', blank=True, null=True, db_index=True)
    value = models.BigIntegerField(blank=True, null=True)
    shares = models.BigIntegerField(blank=True, null=True)
    cik = models.ForeignKey(FundInfo, models.DO_NOTHING, db_column='cik', blank=True, null=True)
    filing_period = models.DateField(blank=True, null=True, db_index=True)

    class Meta:
        managed = False
        db_table = 'position_info'
        indexes = [models.Index(fields=['filing_period']), models.Index(fields=['cusip'])]


class FundStats(models.Model):
    id = models.CharField(max_length=255, blank=True, primary_key=True)
    cik = models.ForeignKey(FundInfo, models.DO_NOTHING, db_column='cik', db_index=True)
    filing_period = models.DateField(db_index=True)
    funds_deployed = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fund_stats'
        unique_together = (('cik', 'filing_period'),)


class SecurityStats(models.Model):
    id = models.CharField(max_length=255, blank=True, primary_key=True)
    cusip = models.ForeignKey(SecurityInfo, models.DO_NOTHING, db_column='cusip', db_index=True)
    filing_period = models.DateField(db_index=True)
    total_shares = models.BigIntegerField(blank=True, null=True)
    total_value = models.BigIntegerField(blank=True, null=True)
    total_count = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'security_stats'
        unique_together = (('cusip', 'filing_period'),)