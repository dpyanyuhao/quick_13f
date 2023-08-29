from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('application_one/', views.application_one, name='application_one'),
    path('get_time_intervals_by_cik/', views.get_time_intervals_by_cik, name='get_time_intervals_by_cik'),
    path('get_fund_holdings_plot/', views.get_fund_holdings_plot, name='get_fund_holdings_plot'),
    path('get_sector_exposure_plot/', views.get_sector_exposure_plot, name='get_sector_exposure_plot'),
    path('get_position_change_table/', views.get_position_change_table, name='get_position_change_table'),
    path('application_two/', views.application_two, name='application_two'),
    path('get_time_intervals_by_cusip/', views.get_time_intervals_by_cusip, name='get_time_intervals_by_cusip'),
    path('get_dollar_notional_plot/', views.get_dollar_notional_plot, name='get_dollar_notional_plot'),
    path('get_top_holders_plot/', views.get_top_holders_plot, name='get_top_holders_plot'),
    path('application_three/', views.application_three, name='application_three'),
    path('get_top_holdings_plot/', views.get_top_holdings_plot, name='get_top_holdings_plot'),
    path('get_top_holdings_time_series/', views.get_top_holdings_time_series, name='get_top_holdings_time_series'),
    path('application_four/', views.application_four, name='application_four'),
    path('get_most_traded_securities_by_quarter/', views.get_most_traded_securities_by_quarter, name='get_most_traded_securities_by_quarter'),
    path('application_five/', views.application_five, name='application_five'),
    path('get_sorted_fund_manager/', views.get_sorted_fund_manager, name='get_sorted_fund_manager'),
    path('application_five_2/', views.application_five_2, name='application_five_2'),
    path('get_aggregate_exposure_plot/', views.get_aggregate_exposure_plot, name='get_aggregate_exposure_plot'),
]