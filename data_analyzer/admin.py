from django.contrib import admin
from .models import FundInfo, FundStats, PositionInfo, SecurityInfo, SecurityStats

admin.site.register(FundInfo)
admin.site.register(FundStats)
admin.site.register(PositionInfo)
admin.site.register(SecurityInfo)
admin.site.register(SecurityStats)