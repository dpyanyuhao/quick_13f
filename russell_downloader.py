import numpy as np
import pandas as pd
import pandas_market_calendars as mcal
from datetime import datetime
import json
import os
import requests
from MySQLdb import _mysql


def get_trading_day_quarter_ends(exchange_code, start_date, end_date, output_format):
    nyse = mcal.get_calendar(exchange_code)
    trading_days_df = pd.DataFrame({'trading_date':
                                        nyse.valid_days(start_date=start_date,
                                                        end_date=end_date)
                                    })

    # This will create a column like '2021Q1', '2021Q2', ...
    trading_days_df['yyQ'] = trading_days_df['trading_date'].dt.to_period("Q").astype(str)

    trading_day_quarter_ends = trading_days_df.groupby('yyQ')['trading_date'].max(). \
        dt.strftime(output_format).to_list()

    return trading_day_quarter_ends


def map_raw_item(unmapped_item):
    return {
        'ticker': unmapped_item[0],
        'name': unmapped_item[1],
        'sector': unmapped_item[2],
        'asset_class': unmapped_item[3],
        'market_value': unmapped_item[4]['raw'],
        'weight': unmapped_item[5]['raw'],
        'notional_value': unmapped_item[6]['raw'],
        'shares': unmapped_item[7]['raw'],
        'cusip': unmapped_item[8],
        'isin': unmapped_item[9],
        'sedol': unmapped_item[10],
        'price': unmapped_item[11]['raw'],
        'location': unmapped_item[12],
        'exchange': unmapped_item[13],
        'currency': unmapped_item[14],
        'fx_rate': unmapped_item[15],
        'maturity': unmapped_item[16]
    }


def format_response(response_json):
    input_items = response_json['aaData']
    output_items = []
    for input_item in input_items:
        mapped_item = map_raw_item(input_item)
        output_items.append(mapped_item)
    return (output_items)


if __name__ == "__main__":
    # INPUTS
    etf_landing_page = 'https://www.ishares.com/us/products/239707/ishares-russell-1000-etf'
    start_date = '2017-12-31'
    end_date = datetime.now().strftime('%Y-%m-%d')

    list_of_holdings = []
    yyyymmdd_queue = get_trading_day_quarter_ends('NYSE', start_date, end_date, '%Y%m%d')

    for yyyymmdd in yyyymmdd_queue:
        request_url = f'{etf_landing_page}/1467271812596.ajax?fileType=json&tab=all&asOfDate={yyyymmdd}'
        print(f'requesting: {request_url}')

        response = requests.get(request_url)

        if response is None:
            print(f'{"!" * 10}\nREQUEST FAILED({yyyymmdd}):\n'
                f'ERROR: Request to SB Timed-Out\n'
                f'{"!" * 10}')
        else:
            print(f'response.status_code: {response.status_code}')

            if response.status_code != 200:

                print(f'{"!" * 10}\nREQUEST FAILED({yyyymmdd}):\n'
                    f'status code = {response.status_code}\n'
                    f'response_message = {response.text}\n'
                    f'{"!" * 10}')
            else:
                response_json = json.loads(response.content)
                holdings_json = format_response(response_json)
                holdings_df = pd.DataFrame(holdings_json)

                if holdings_df.shape[0] == 0:
                    print(f'{"!" * 10}\nERROR: 0 ROWS ({yyyymmdd})\n{"!" * 10}')

                else:
                    print(f'number of rows: {holdings_df.shape[0]}')

                    # add date col
                    holdings_df.insert(loc=0,
                                    column='as_of_date',
                                    value=f'{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}')  # %Y-%m-%d
                    list_of_holdings.append(holdings_df)
        
    holdings = pd.concat(list_of_holdings)
    clean_holdings = holdings[(holdings['asset_class'] == "Equity") & (holdings['ticker'] != "-") & (holdings['cusip'] != "-")]
    # Group by 'ticker' and aggregate using first non-NA value
    security_data = clean_holdings.groupby('cusip').agg({
        'ticker': 'last',
        'name': 'last',
        'sector': 'last',
        'asset_class': 'last',
        'location': 'last',
        'exchange': 'last'
    }).reset_index()

    # Connecting to the MySQL server
    db = _mysql.connect(host="localhost", user="root", password="password")

    try:
        # Select the database
        db.query("USE filings_13f")
    except _mysql.OperationalError:
        db.query("CREATE DATABASE filings_13f")
        db.query("USE filings_13f")
        
    # Query to create the security_info table
    create_table_query = """
    CREATE TABLE IF NOT EXISTS security_info (
        cusip CHAR(9) PRIMARY KEY NOT NULL,
        ticker VARCHAR(255),
        name VARCHAR(255),
        sector VARCHAR(255),
        asset_class VARCHAR(255),
        location VARCHAR(255),
        exchange VARCHAR(255)
    );
    """

    db.query(create_table_query)

    # Iterate through each row in the DataFrame
    for index, row in security_data.iterrows():
        cusip_value = row['cusip']
        
        # Check if the record already exists in the table
        result = db.query(f"SELECT 1 FROM security_info WHERE cusip = '{cusip_value}'")
        
        if db.use_result().num_rows():
            print(cusip_value, "already exists")
        else:
            # If not, insert the row to the table
            try:
                insert_query = f"""
                INSERT INTO security_info (
                    cusip,
                    ticker,
                    name,
                    sector,
                    asset_class,
                    location,
                    exchange
                ) 
                VALUES (
                    '{row['cusip']}',
                    '{row['ticker']}',
                    '{row['name']}',
                    '{row['sector']}',
                    '{row['asset_class']}',
                    '{row['location']}',
                    '{row['exchange']}'
                )
                """
                db.query(insert_query)
            except _mysql.MySQLError as e:
                print("Insert failed", e)

