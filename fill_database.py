import os
import re
import pandas as pd
import MySQLdb


if __name__ == "__main__":
    folders_to_process = []

    print("Entered")

    for folder in os.listdir(os.getcwd()):
        # Check if the folder matches the pattern eg. 2018q1_form13f
        if re.match(r'\d{4}q[1-4]_form13f', folder):
            # Construct full folder path
            folder_path = os.path.join(os.getcwd(), folder)
            if os.path.isdir(folder_path):
                folders_to_process.append(folder_path)
    
    print(folders_to_process)
    
    valid_dates = {'31-MAR-2018', '30-JUN-2018', '30-SEP-2018', '31-DEC-2018', 
                   '31-MAR-2019', '30-JUN-2019', '30-SEP-2019', '31-DEC-2019', 
                   '31-MAR-2020', '30-JUN-2020', '30-SEP-2020', '31-DEC-2020', 
                   '31-MAR-2021', '30-JUN-2021', '30-SEP-2021', '31-DEC-2021', 
                   '31-MAR-2022', '30-JUN-2022', '30-SEP-2022', '31-DEC-2022'
                   }
    
    # Connecting to the MySQL server
    connection = MySQLdb.connect(host="localhost", user="root", password="password", database="filings_13f")
    cursor = connection.cursor()

    # Create table security_info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_info (
        cusip CHAR(9) PRIMARY KEY,
        ticker VARCHAR(255),
        name VARCHAR(255),
        sector VARCHAR(255),
        asset_class VARCHAR(255),
        location VARCHAR(255),
        exchange VARCHAR(255)
    )
    """)

    # Create table fund_info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fund_info (
        cik INTEGER PRIMARY KEY,
        manager_name VARCHAR(255),
        city VARCHAR(255)
    )
    """)

    # Create table position_info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS position_info (
        infotable_sk INTEGER PRIMARY KEY,
        accession_number VARCHAR(255),
        cusip CHAR(9),
        value BIGINT,
        shares BIGINT,
        cik INTEGER,
        filing_period DATE,
        FOREIGN KEY (cusip) REFERENCES security_info(cusip),
        FOREIGN KEY (cik) REFERENCES fund_info(cik)
    )
    """)

    try:
        cursor.execute("""
        CREATE INDEX idx_filing_period
        ON position_info(filing_period)
        """)
        connection.commit()
    except MySQLdb.OperationalError as e:
        # 1061 corresponds to 'Duplicate key name', the index already exists
        if e.args[0] != 1061:  
            raise

    # Create table security_stats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS security_stats (
        cusip CHAR(9),
        filing_period DATE,
        total_shares BIGINT,
        total_value BIGINT,
        total_count INTEGER,
        PRIMARY KEY (cusip, filing_period),
        FOREIGN KEY (cusip) REFERENCES security_info(cusip)
    )
    """)

    # Create table fund_stats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fund_stats (
        cik INTEGER,
        filing_period DATE,
        funds_deployed BIGINT,
        PRIMARY KEY (cik, filing_period),
        FOREIGN KEY (cik) REFERENCES fund_info(cik)
    )
    """)

    # Committing changes
    connection.commit()

    # Query to get all 'cusip' values from 'security_info' table
    cursor.execute("SELECT cusip FROM security_info")

    # Fetch all rows
    rows = cursor.fetchall()

    # Convert rows to a set of 'cusip' values
    cusips = {row[0] for row in rows}

    infotable_columns = ['ACCESSION_NUMBER', 'INFOTABLE_SK', 'CUSIP', 'VALUE', 'SSHPRNAMT', 'SSHPRNAMTTYPE', 'PUTCALL']
    submissions_columns = ['ACCESSION_NUMBER', 'SUBMISSIONTYPE', 'CIK', 'PERIODOFREPORT']
    coverpage_columns = ['ACCESSION_NUMBER', 'FILINGMANAGER_NAME', 'FILINGMANAGER_CITY']
    grouping_columns = ['ACCESSION_NUMBER', 'CUSIP', 'SSHPRNAMTTYPE', 'SUBMISSIONTYPE', 
                        'CIK', 'PERIODOFREPORT', 'FILINGMANAGER_NAME', 'FILINGMANAGER_CITY']
    
    for quarter in folders_to_process:

        # We need to catch the change in 13F filing format
        year = int(quarter[-14:-10])

        infotable = pd.read_csv(os.path.join(quarter, 'INFOTABLE.tsv'), sep='\t', usecols=infotable_columns)
        submissions = pd.read_csv(os.path.join(quarter, 'SUBMISSION.tsv'), sep='\t', usecols=submissions_columns)
        coverpage = pd.read_csv(os.path.join(quarter, 'COVERPAGE.tsv'), sep='\t', usecols=coverpage_columns)

        # Convert the relevant columns to integers
        coverpage['FILINGMANAGER_NAME'] = coverpage['FILINGMANAGER_NAME'].str.upper()
        coverpage['FILINGMANAGER_CITY'] = coverpage['FILINGMANAGER_CITY'].str.upper()

        valid_filings = submissions.query("SUBMISSIONTYPE == '13F-HR' and PERIODOFREPORT in @valid_dates")
        filtered_infotable = infotable[infotable['CUSIP'].isin(cusips) & 
                                        pd.isna(infotable['PUTCALL']) &  
                                        (infotable['SSHPRNAMTTYPE'] == 'SH')]
        valid_infotable = pd.merge(filtered_infotable, valid_filings, on='ACCESSION_NUMBER', how='inner')
        all_data = pd.merge(valid_infotable, coverpage, on='ACCESSION_NUMBER', how='left')
        all_data = all_data.groupby(grouping_columns, as_index=False).agg({'VALUE': 'sum',
                                                                        'SSHPRNAMT': 'sum',
                                                                        'INFOTABLE_SK': 'first'})
        all_data['PERIODOFREPORT'] = pd.to_datetime(all_data['PERIODOFREPORT'], format='%d-%b-%Y').dt.strftime('%Y-%m-%d')

        # Group by CIK, PERIODOFREPORT, and SUBMISSIONTYPE
        grouped = submissions.groupby(['CIK', 'PERIODOFREPORT', 'SUBMISSIONTYPE'])['ACCESSION_NUMBER'].apply(list).unstack()

        # Filtering only the rows where both '13F-HR' and '13F-HR/A' exist and making the dictionary
        amended_dict = {row['13F-HR'][0]: row['13F-HR/A'][0] for _, row in grouped.dropna(subset=['13F-HR', '13F-HR/A']).iterrows()}

        all_data['amended_acc_num'] = all_data['ACCESSION_NUMBER'].map(amended_dict)

        merged_data = pd.merge(
            all_data,
            infotable[['ACCESSION_NUMBER', 'CUSIP', 'VALUE', 'SSHPRNAMT']],
            left_on=['amended_acc_num', 'CUSIP'],
            right_on=['ACCESSION_NUMBER', 'CUSIP'],
            suffixes=('', '_CORRECTED'),
            how='left'
        )

        # Fill NaNs in the merged columns
        merged_data['VALUE_CORRECTED'].fillna(merged_data['VALUE'], inplace=True)
        merged_data['SSHPRNAMT_CORRECTED'].fillna(merged_data['SSHPRNAMT'], inplace=True)

        if year <= 2022:
            merged_data['VALUE_CORRECTED'] = merged_data['VALUE_CORRECTED'] * 1000

        merged_data = merged_data[(merged_data['VALUE_CORRECTED'] != 0) & (merged_data['SSHPRNAMT_CORRECTED'] != 0)]
        merged_data['VALUE_CORRECTED'] = merged_data['VALUE_CORRECTED'].astype('int64')
        merged_data['SSHPRNAMT_CORRECTED'] = merged_data['SSHPRNAMT_CORRECTED'].astype('int64')

        merged_data['PRICE'] = merged_data['VALUE_CORRECTED']/merged_data['SSHPRNAMT_CORRECTED']
        median_prices = merged_data.groupby('CUSIP')['PRICE'].median()
        merged_data['median_price'] = merged_data['CUSIP'].map(median_prices)
        merged_data['change_base'] = (merged_data['PRICE'] / merged_data['median_price']).apply(lambda x: not (0.5 <= x <= 1.5))
        merged_data.loc[merged_data['change_base']==True, 'VALUE_CORRECTED'] = (merged_data['median_price'] * merged_data['SSHPRNAMT_CORRECTED']).round()

        for index, row in merged_data.iterrows():

            if index % 5000 == 0:
                print(index)

             # Insert to fund_info table
            try:
                cursor.execute("""
                INSERT IGNORE INTO fund_info (cik, manager_name, city)
                VALUES (%s, %s, %s)
                """, (row['CIK'], row['FILINGMANAGER_NAME'], row['FILINGMANAGER_CITY']))
            except MySQLdb.Error as e:
                print(f"Error inserting into fund_info: {e}")
            
            # Insert to position_info table
            try:
                cursor.execute("""
                INSERT IGNORE INTO position_info (infotable_sk, accession_number, cusip, value, shares, CIK, filing_period)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (row['INFOTABLE_SK'], row['ACCESSION_NUMBER'], row['CUSIP'], row['VALUE_CORRECTED'], row['SSHPRNAMT_CORRECTED'], row['CIK'], row['PERIODOFREPORT']))
            except MySQLdb.Error as e:
                print(f"Error inserting into position_info: {e}")

            # Populating the security_stats table
            try:
                cursor.execute("""
                INSERT INTO security_stats (cusip, filing_period, total_shares, total_value, total_count)
                VALUES (%s, %s, %s, %s, 1)
                ON DUPLICATE KEY UPDATE
                total_shares = total_shares + VALUES(total_shares),
                total_value = total_value + VALUES(total_value),
                total_count = total_count + 1
                """, (row['CUSIP'], row['PERIODOFREPORT'], row['SSHPRNAMT_CORRECTED'], row['VALUE_CORRECTED']))
            except MySQLdb.Error as e:
                print(f"Error inserting/updating security_stats: {e}")
            
            # Populating the fund_stats table
            try:
                cursor.execute("""
                INSERT INTO fund_stats (cik, filing_period, funds_deployed)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE
                funds_deployed = funds_deployed + VALUES(funds_deployed)
                """, (row['CIK'], row['PERIODOFREPORT'], row['VALUE_CORRECTED']))
            except MySQLdb.Error as e:
                print(f"Error inserting/updating fund_stats: {e}")
            
        # Committing changes
        connection.commit()
        
        print(f"{quarter} completed.")

    # Close the cursor and the connection
    cursor.close()
    connection.close()