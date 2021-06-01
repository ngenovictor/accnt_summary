import argparse
import camelot
import PyPDF2
import pikepdf
import os
import pandas as pd
import numpy as np

import typing

SUPPORTED_FILE_TYPES = ['safaricom', 'kcb']


def parse_safaricom_statement(password, file_path):
    all_sum = dict()
    with pikepdf.open(file_path, password=password) as pdf:
        server_file_path = file_path.replace(".pdf", "_decrypt.pdf")
        pdf.save(server_file_path)
        tables = camelot.read_pdf(server_file_path, pages='all', password=password)
        all_tables = pd.DataFrame()
        for table in tables:
            table_df = table.df
            columns = list(table_df.iloc[0])[0].split('\n')[:-1]
            if 'Completion Time' not in columns:
                continue
            table_df = table_df[1:]
            table_df.columns = columns
            all_tables = all_tables.append(table_df)
        
        def extract_counts(df_row):
            date = df_row['Completion Time'][:7]
            all_sum.setdefault(date, {'Paid In': 0, 'Withdrawn': 0})
            if df_row['Paid In']:
                all_sum[date]['Paid In'] = all_sum[date]['Paid In'] + float(df_row['Paid In'].replace(',', ''))
            if df_row['Withdrawn']:
                all_sum[date]['Withdrawn'] = all_sum[date]['Withdrawn'] + float(df_row['Withdrawn'].replace(',', ''))

        all_tables.apply(extract_counts, axis=1)
        os.remove(server_file_path)
        
    return all_sum


def parse_kcb_statement(file_path: str) -> typing.Dict:
    all_sum = dict()
    tables = camelot.read_pdf(file_path, pages='1,2', flavor='stream')
    all_tables = pd.DataFrame()
    
    def _extract_counts(df_row):
        month = df_row['TXN DATE'][3:]
        all_sum.setdefault(month, {'MONEY OUT': 0, 'MONEY IN': 0})
        if not pd.isna(df_row['MONEY OUT']):
            all_sum[month]['MONEY OUT'] = all_sum[month]['MONEY OUT'] + float(df_row['MONEY OUT'].replace(',', ''))
        if not pd.isna(df_row['MONEY IN']):
            all_sum[month]['MONEY IN'] = all_sum[month]['MONEY IN'] + float(df_row['MONEY IN'].replace(',', ''))
    
    for idx, table in enumerate(tables):
        table_df = table.df
        if idx == 0:
            columns = list(tables[0].df.iloc[8])
            assert columns == ['TXN DATE', 'DESCRIPTION', 'VALUE DATE', 'MONEY OUT', 'MONEY IN', '', 'LEDGER BALANCE']
            table_df = table_df[9:]
            table_df.columns = columns
            # drop the empty column
            table_df = table_df.drop('MONEY IN', axis='columns')
            # rename the '' column to MONEY IN
            table_df = table_df.rename(columns={'': 'MONEY IN'})
            columns = list(table_df.columns)
        
        table_df.columns = columns
        # drop na in TXN DATE column to remain with relevant columns
        table_df = table_df.replace('', np.nan)
        table_df = table_df.dropna(subset=['TXN DATE'])
        all_tables = all_tables.append(table_df)
        
    all_tables.apply(_extract_counts, axis=1)
    return all_sum

def parse_account_statement(file_type, password, file_path):
    if file_type == 'safaricom':
        return parse_safaricom_statement(password, file_path)
    elif file_type == 'kcb':
        return parse_kcb_statement(file_path)
    else:
        raise NotImplementedError()
        

def is_pdf_file(parser, arg):
    if not str(arg).endswith(".pdf"):
        parser.error(f"The file {arg} is not a pdf!")
    else:
        return arg

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Script to read statement pdf files and give a summary of totals per month.")
    parser.add_argument("--type","-t", choices=SUPPORTED_FILE_TYPES, help=f"Source of the file. Supported are : {SUPPORTED_FILE_TYPES}", required=True)
    parser.add_argument("--password", "-p", help="Required for encrypted files. Especially safcom files.")
    parser.add_argument("--file_path", '-f', help="Path to the pdf file to scan", type=lambda x: is_pdf_file(parser, x)  ,required=True)
    args = parser.parse_args()
    for month, values in parse_account_statement(args.type, args.password, args.file_path).items():
        print(f"{month} ==> {values}")
    # 11038100