from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import F, IntegerField, Max, Sum, Value, When, Window
from django.db.models.functions import RowNumber
from .models import FundInfo, FundStats, PositionInfo, SecurityInfo, SecurityStats
import plotly.express as px
import pandas as pd


def index(request):
    return render(request, 'index.html')

def application_one(request):
    funds = FundInfo.objects.all().order_by('manager_name')
    return render(request, 'application_one.html', {'funds': funds})

def get_time_intervals_by_cik(request):
    cik = request.GET.get('cik')
    intervals = FundStats.objects.filter(cik=cik).values_list('filing_period', flat=True).distinct().order_by('filing_period')
    return JsonResponse({'intervals': list(intervals)})

def get_fund_holdings_plot(request):
    cik = int(request.GET.get('cik'))
    positions = PositionInfo.objects.filter(cik=cik)
    positions_with_security_info = positions.values('cusip__ticker', 'cusip__name', 'cusip__sector', 'value', 'shares', 'filing_period').order_by('filing_period')

    df = pd.DataFrame(positions_with_security_info)
    df = df.sort_values('cusip__name')
    fig = px.area(df, x="filing_period", y="value", color="cusip__name")
    fig.update_traces(mode="markers+lines", hovertemplate=None)
    fig.update_layout(hovermode="x")

    fig.update_layout(
        xaxis_title="Period",
        yaxis_title="Total Value",
        legend_title_text="Holdings"
        )
    
    fig.update_layout(
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=3, label="3m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all", label="All")
                    ])
                    ),
            rangeslider=dict(visible=True),
            type="date"
            )
        )
     
    fig.update_layout(
        updatemenus=[
            dict(
                type='buttons',
                showactive=False,
                x=1.3,
                y=-0.1,
                buttons=[
                    dict(label='Show All',
                        method='restyle',
                        args=['visible', [True for trace in fig.data]]),
                    dict(label='Hide All',
                        method='restyle',
                        args=['visible', ['legendonly' for trace in fig.data]])
                    ]
                )
            ]
        )

    plot = fig.to_html(full_html=False, default_height=500, default_width=800)
    return JsonResponse({"plot": plot})

def get_sector_exposure_plot(request):
    cik = int(request.GET.get('cik'))
    positions = PositionInfo.objects.filter(cik=cik)
    positions_with_security_info = positions.values('cusip__ticker', 'cusip__name', 'cusip__sector', 'value', 'shares', 'filing_period').order_by('filing_period')

    df = pd.DataFrame(positions_with_security_info)
    aggregated = df.groupby(['cusip__sector', 'filing_period'])['value'].sum().reset_index()

    total_per_period = aggregated.groupby('filing_period')['value'].sum().reset_index()
    total_per_period = total_per_period.rename(columns={'value': 'total_value'})

    merged = pd.merge(aggregated, total_per_period, on='filing_period')
    merged['percentage'] = (merged['value'] / merged['total_value']) * 100
    merged['percentage_text'] = merged['percentage'].apply(lambda x: f"{x:.2f}%")

    merged = merged.sort_values(by='cusip__sector')

    fig = px.bar(merged, 
                 y="filing_period", 
                 x="percentage", 
                 color="cusip__sector", 
                 orientation="h",
                 title="Sector Exposure by Filing Period",
                 hover_data={"cusip__sector": True,
                             "percentage": False,
                             "percentage_text": True,
                             "filing_period": True},
                 labels={'cusip__sector': 'Sector',
                         'percentage_text': 'Weight',
                         'filing_period': 'Period'}
              )
    
    fig.update_layout(
        xaxis_title="% of holdings",
        yaxis_title="Filing Period",
        legend_title_text="Sector"
        )
    
    fig.update_layout(barmode='stack')
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)
    return JsonResponse({"plot": plot})

def get_position_change_table(request):
    cik = int(request.GET.get('cik'))
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    current_positions = PositionInfo.objects.filter(cik=cik, filing_period=start_time)
    previous_positions = PositionInfo.objects.filter(cik=cik, filing_period=end_time)

    prev_data = {pos.cusip_id: pos for pos in previous_positions}
    current_data = {pos.cusip_id: pos for pos in current_positions}

    results = []

    for pos in current_positions:
        ticker = pos.cusip.ticker
        stock_name = pos.cusip.name
        value = pos.value
        shares = pos.shares
        prev_shares = prev_data.get(pos.cusip_id).shares if pos.cusip_id in prev_data else 0
        change_in_shares = shares - prev_shares
        percent_change = round((shares - prev_shares) / prev_shares * 100, 2) if prev_shares != 0 else "NEW"
        percent_of_company = round((value / sum([p.value for p in current_positions])) * 100, 2)

        results.append({
            'stock_name': stock_name,
            'ticker': ticker,
            'value': value,
            'shares': shares,
            '% change in shares': percent_change,
            'absolute change in shares': change_in_shares,
            '% of company': percent_of_company
        })
    
    for pos in previous_positions:
        if pos.cusip_id not in current_data:
            ticker = pos.cusip.ticker
            stock_name = pos.cusip.name
            prev_shares = pos.shares

            # These positions were sold, so their current value, shares, and % of company are 0
            results.append({
                'stock_name': stock_name,
                'ticker': ticker,
                'value': 0,
                'shares': 0,
                '% change in shares': -100,  # Because it was sold
                'absolute change in shares': -prev_shares,  # Negative of previous shares
                '% of company': 0
            })
    
    sorted_results = sorted(results, key=lambda x: x['% of company'], reverse=True)

    return JsonResponse({'data': sorted_results})

def application_two(request):
    securities = SecurityInfo.objects.all().order_by('name')
    return render(request, 'application_two.html', {'securities': securities})

def get_time_intervals_by_cusip(request):
    cusip = request.GET.get('cusip')
    intervals = SecurityStats.objects.filter(cusip=cusip).values_list('filing_period', flat=True).distinct().order_by('filing_period')
    return JsonResponse({'intervals': list(intervals)})

def get_dollar_notional_plot(request):
    cusip = request.GET.get('cusip')
    start_time = request.GET.get('start_time')
    end_time = request.GET.get('end_time')

    positions = PositionInfo.objects.filter(
        cusip=cusip,
        filing_period__range =[start_time, end_time]
    ).order_by('filing_period')
   
    df = pd.DataFrame(positions.values())

    data_points = df.groupby('filing_period').agg({'value': 'sum', 'shares': 'sum'}).reset_index()

    # Compute the $ notional bought/sold
    data_points['price'] = data_points['value']/data_points['shares']
    data_points['delta_shares'] = data_points['shares'].diff().fillna(0)
    data_points['notional'] = data_points['delta_shares'] * data_points['price']
    data_points['notional'] = data_points['notional'].round(2)

    fig = px.line(data_points, 
                  x='filing_period', 
                  y='notional', 
                  title="$ Notional Bought/Sold over Period",
                  labels={'filing_period': 'Period',
                          'notional': 'Notional Bought/Sold'
                          }
                )
    fig.update_layout(
        xaxis_title="Filing Period",
        yaxis_title="$ Notional Bought/Sold"
        )
    fig.update_xaxes(rangeslider_visible=True)
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)

    chart_data = data_points[['filing_period', 'value', 'shares', 'notional']].to_dict('records')

    return JsonResponse({"plot": plot, "chart_data": chart_data})

def get_top_holders_plot(request):
    cusip = request.GET.get('cusip')
    num_of_funds = int(request.GET.get('num_of_funds'))

    # Get top n positions for each period in a single query using annotations and Subquery
    top_positions = (
        PositionInfo.objects
        .filter(cusip=cusip)
        .annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=F('value').desc(),
                partition_by=F('filing_period')
            )
        )
        .filter(rank__lte=num_of_funds)
        .values('cusip', 'value', 'shares', 'cik', 'filing_period', 'cik__manager_name')
        .order_by('-value')
    )

    # Convert the queryset directly to DataFrame
    data = pd.DataFrame(top_positions)

    fig = px.bar(data, 
                 y="filing_period", 
                 x="value",
                 color="cik__manager_name", 
                 orientation="h",
                 title="Top Holders by Period",
                 hover_data={"cik__manager_name": True,
                             "value": True,
                             "filing_period": True,
                             "cik": True},
                 labels={'cik__manager_name': 'Fund',
                         'value': 'Value',
                         'filing_period': 'Period',
                         'cik': 'CIK'}
    )

    fig.update_layout(
        xaxis_title="Value",
        yaxis_title="Filing Period",
        legend_title_text="Fund Name"
        )

    fig.update_layout(barmode='stack')
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)

    return JsonResponse({"plot": plot})

def application_three(request):
    intervals = PositionInfo.objects.values_list('filing_period', flat=True).distinct().order_by('filing_period')
    return render(request, 'application_three.html', {'intervals': intervals})

def get_top_holdings_plot(request):
    top_number = int(request.GET.get('number'))

    # Annotate the data with a row number partitioned by the filing period and ordered by total_value
    annotated_securities = SecurityStats.objects.annotate(
        row_number=Window(
            expression=RowNumber(),
            partition_by=[F('filing_period')],
            order_by=F('total_value').desc()
        )
    ).filter(row_number__lte=top_number)

    df = pd.DataFrame(annotated_securities.values('cusip__name', 'cusip__ticker', 'filing_period', 'total_value'))

    fig = px.bar(df, 
                y="filing_period", 
                x="total_value",
                color="cusip__name", 
                orientation="h",
                title="Top Holdings by Period",
                hover_data={"cusip__name": True,
                            "cusip__ticker": True,
                            "filing_period": True,
                            "total_value": True},
                labels={'cusip__name': 'Name',
                        'cusip__ticker': 'Ticker',
                        'filing_period': 'Period',
                        'total_value': 'Aggregated Notional'}
    )

    fig.update_layout(
        xaxis_title="Value",
        yaxis_title="Filing Period",
        legend_title_text="Security Name"
        )
    
    fig.update_layout(barmode='stack')
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)
    
    return JsonResponse({"plot": plot})

def get_top_holdings_time_series(request):
    top_number = int(request.GET.get('number'))
    filing_period = request.GET.get('time')
    top_cusips = list(SecurityStats.objects.filter(filing_period=filing_period).order_by('-total_value').values_list('cusip', flat=True)[:top_number])
    security_stats = SecurityStats.objects.filter(cusip__in=top_cusips).values('cusip__name', 'cusip__ticker', 'filing_period', 'total_value')

    df = pd.DataFrame(security_stats)

    fig = px.line(df, 
                  x='filing_period', 
                  y='total_value', 
                  color='cusip__name',
                  title="Change in $ Notional",
                  labels={
                        "cusip__name": "Name",
                        "cusip__ticker": "Ticker",
                        "filing_period": "Filing Period",
                        "total_value": "Total Value"
                    },
                  hover_data={
                      "cusip__name": True,
                      "cusip__ticker": True,
                      "filing_period": True,
                      "total_value": True,
                      }
                  )
    
    fig.update_layout(
        xaxis_title="Filing Period",
        yaxis_title="Total Value",
        legend_title_text="Security Name"
        )
    
    fig.update_xaxes(rangeslider_visible=True)
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)

    top_owned_cusips = list(SecurityStats.objects.filter(filing_period=filing_period).order_by('-total_count').values_list('cusip', flat=True)[:top_number])
    owned_stats = SecurityStats.objects.filter(cusip__in=top_owned_cusips).values('cusip__name', 'cusip__ticker', 'filing_period', 'total_count')

    df2 = pd.DataFrame(owned_stats)

    # Create a new column for the descriptive hover text
    df2['Owned by'] = df2['total_count'].apply(lambda x: f"{x} companies")

    fig2 = px.line(df2, 
                x='filing_period', 
                y='total_count', 
                color='cusip__name',
                title="Most Owned Securities",
                labels={
                    "cusip__name": "Name",
                    "cusip__ticker": "Ticker",
                    "filing_period": "Filing Period",
                },
                hover_data={
                    "cusip__name": True,
                    "cusip__ticker": True,
                    "filing_period": True,
                    "Owned by": True,
                    'total_count': False,
                }
    )

    fig2.update_layout(
        xaxis_title="Filing Period",
        yaxis_title="Total Count",
        legend_title_text="Security Name"
        )

    fig2.update_xaxes(rangeslider_visible=True)
    plot2 = fig2.to_html(full_html=False, default_height=500, default_width=800)

    return JsonResponse({'notionalplot': plot, 'ownedplot': plot2})

def application_four(request):
    intervals = PositionInfo.objects.values_list('filing_period', flat=True).distinct().order_by('filing_period')
    return render(request, 'application_four.html', {'intervals': intervals})

def get_most_traded_securities_by_quarter(request):
    num_of_funds = int(request.GET.get('num_of_funds'))
    time = request.GET.get('time')
    previous_date = PositionInfo.objects.filter(filing_period__lt=time).aggregate(max_filing_period=Max('filing_period'))['max_filing_period']
    
    current_quarter_data = SecurityStats.objects.filter(filing_period=time)
    last_quarter_data = SecurityStats.objects.filter(filing_period=previous_date)

    previous_dict = {pos.cusip.cusip: pos for pos in last_quarter_data}
    results = []

    for security_stat in current_quarter_data:
        cusip = security_stat.cusip.cusip
        ticker = security_stat.cusip.ticker
        stock_name = security_stat.cusip.name
        total_value = security_stat.total_value
        total_shares = security_stat.total_shares
        previous_shares = previous_dict.pop(cusip, None).total_shares if cusip in previous_dict else 0
        change_in_shares = total_shares - previous_shares

        results.append({
            'stock_name': stock_name,
            'ticker': ticker,
            'total_value': total_value,
            'total_shares': total_shares,
            'change_in_shares': change_in_shares,
        })

    for remaining_stat in previous_dict.values():
        ticker = remaining_stat.cusip.ticker
        stock_name = remaining_stat.cusip.name
        total_shares = remaining_stat.total_shares

        results.append({
            'stock_name': stock_name,
            'ticker': ticker,
            'total_value': 0,
            'total_shares': 0,
            'change_in_shares': -total_shares,
        })

     # Sort results for table1_data (largest change in shares) and limit by num_of_funds
    table1_data = sorted(results, key=lambda x: x['change_in_shares'], reverse=True)[:num_of_funds]
    
    # Sort results for table2_data (smallest change in shares) and limit by num_of_funds
    table2_data = sorted(results, key=lambda x: x['change_in_shares'])[:num_of_funds]

    return JsonResponse({"time": time, "table1_data": table1_data, "table2_data": table2_data})

def application_five(request):
    intervals = PositionInfo.objects.values_list('filing_period', flat=True).distinct().order_by('filing_period')
    return render(request, 'application_five.html', {'intervals': intervals})

def get_sorted_fund_manager(request):
    time = request.GET.get('time')
    funds = FundStats.objects.filter(filing_period=time).order_by('-funds_deployed')

    paginator = Paginator(funds, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    fund_data = [
        {
            'cik': fund.cik.cik,
            'manager_name': fund.cik.manager_name
        } 
        for fund in page_obj
    ]

    return JsonResponse({
        'data': fund_data,
        'page_number': page_obj.number,
        'num_pages': page_obj.paginator.num_pages,
        'has_next': page_obj.has_next(),
        'has_previous': page_obj.has_previous(),
    })

def application_five_2(request):
    if request.method == 'POST':
        # Extract the selected time and fund list from POST data
        selected_time = request.POST.get('selectedTime')
        fund_list = request.POST.getlist('fund_list')
        fund_list = [int(cik) for cik in fund_list]

        # Filter and aggregate
        largest_holdings = PositionInfo.objects.filter(cik__in=fund_list, filing_period=selected_time).values('cusip', 'cusip__name', 'cusip__ticker').annotate(total_value=Sum('value')).order_by('-total_value')
        selected_funds = FundInfo.objects.filter(cik__in=fund_list).values('cik', 'manager_name').order_by('manager_name')

        context = {
            'time': selected_time,
            'fund_list': selected_funds,
            'holdings': largest_holdings
        }

        return render(request, 'application_five_2.html', context)
    else:
        return HttpResponse("Invalid request method", status=400)

def get_aggregate_exposure_plot(request):
    selected_cusips = request.GET.getlist('cusips[]')
    ciks = request.GET.getlist('cik[]')
    selected_ciks = [int(cik) for cik in ciks]

    positions = PositionInfo.objects.filter(cik__in=selected_ciks, cusip__in=selected_cusips).values('cik__manager_name', 'filing_period').annotate(total_value=Sum('value'), total_shares=Sum('shares'))
    df = pd.DataFrame(positions)
    df['period_total_value'] = df.groupby('filing_period')['total_value'].transform('sum')
    df['period_total_shares'] = df.groupby('filing_period')['total_shares'].transform('sum')

    fig = px.area(df, 
                  x="filing_period", 
                  y="total_value",
                  color="cik__manager_name", 
                  title="Aggregate Notional of Select Holdings of Selected Funds",
                  hover_data={"cik__manager_name": True,
                              "total_value": True,
                              "filing_period": True,
                              "period_total_value": True
                              },
                  labels={'cik__manager_name': 'Fund',
                          'total_value': 'Total Value',
                          'filing_period': 'Period',
                          'period_total_value': 'Aggregate Total Notional'
                         },           
    )

    fig.update_layout(
        xaxis_title="Total Value",
        yaxis_title="Filing Period",
        legend_title_text="Fund Name"
        )
    
    fig.update_xaxes(rangeslider_visible=True)
    plot = fig.to_html(full_html=False, default_height=500, default_width=800)

    fig2 = px.area(df, 
                 x="filing_period", 
                 y="total_shares",
                 color="cik__manager_name", 
                 title="Aggregate Shares of Select Holdings of Selected Funds",
                 hover_data={"cik__manager_name": True,
                             "total_shares": True,
                             "filing_period": True,
                             "period_total_shares": True
                             },
                 labels={'cik__manager_name': 'Fund',
                         'total_shares': 'Total Shares',
                         'filing_period': 'Period',
                         'period_total_shares': 'Aggregate Total Shares'
                         },           
    )

    fig2.update_layout(
        xaxis_title="Total Shares",
        yaxis_title="Filing Period",
        legend_title_text="Fund Name"
        )
    
    fig2.update_xaxes(rangeslider_visible=True)
    plot2 = fig2.to_html(full_html=False, default_height=500, default_width=800)

    return JsonResponse({"notionalplot": plot, "sharesplot": plot2})

