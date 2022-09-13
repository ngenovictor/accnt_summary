import argparse
from ast import arg
import camelot
import PyPDF2
from PyPDF2 import parse_filename_page_ranges
import pikepdf
from pikepdf import Pdf
import os
import pandas as pd
import numpy as np
from collections import OrderedDict

import typing

SUPPORTED_FILE_TYPES = ['safaricom', 'kcb', 'equity']


def parse_safaricom_statement(password, file_path):
    all_sum = dict()
    with pikepdf.open(file_path, password=password) as pdf:
        server_file_path = file_path.replace(".pdf", "_decrypt.pdf")
        pdf.save(server_file_path)
        tables = camelot.read_pdf(server_file_path, pages='all', password=password)
        all_tables = pd.DataFrame()
        for table in tables:
            table_df = table.df
            columns = list(table_df.iloc[0])[0].split('\n')
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
    tables = camelot.read_pdf(file_path, pages='all', flavor='stream')
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

def to_float(value):
    return float(value.replace(",", ""))

def parse_equity_statement(file_path, first_transaction_type):
    all_sum = dict()
    with Pdf.open(file_path) as pdf_file:
        pages = len(pdf_file.pages)
    cols_to_ignore = [1,2,3]
    current_balance = None
    for page in range(1, pages+1):
        df = camelot.read_pdf(file_path, pages=f"{page}")[0].df
        headers = list(df.iloc[0][0].split("\n")[:-1])
        headers_to_remove = []
        for idx in cols_to_ignore:
            headers_to_remove.append(headers[idx])
        for header in headers_to_remove:
            headers.remove(header)
        df = df.iloc[1:]  # ignore header processed above
        df = df.drop(cols_to_ignore, axis=1)
        df.columns = headers
        dates = df['Tran Date'].values[0].split("\n")
        debits = df['Debit'].values[0].split("\n")
        credits = df['Credit'].values[0].split("\n")
        balances = df['Balance'].values[0].split("\n")
        for date in dates:
            date = date[3:]
            all_sum.setdefault(date, {"credit": 0, "debit": 0})
            if current_balance is None:
                if first_transaction_type == "credit":
                    current_balance = to_float(balances.pop(0))
                    all_sum[date]["credit"] += to_float(credits.pop(0))
                elif first_transaction_type == "debit":
                    current_balance = to_float(balances.pop(0))
                    all_sum[date]["debit"] += to_float(debits.pop(0))
                else:
                    raise ValueError("first_transaction_type required for equity files")
                continue
            new_balance = to_float(balances.pop(0))
            if new_balance > current_balance:
                all_sum[date]["credit"] += to_float(credits.pop(0))
            else:
                 all_sum[date]["debit"] += to_float(debits.pop(0))
            current_balance = new_balance
    return all_sum

def parse_account_statement(file_type, password, file_path, first_transaction_type):
    if file_type == 'safaricom':
        return parse_safaricom_statement(password, file_path)
    elif file_type == 'kcb':
        return parse_kcb_statement(file_path)
    elif file_type == 'equity':
        return parse_equity_statement(file_path, first_transaction_type)
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
    parser.add_argument("--first_transaction_type", choices=("debit", "credit"), help="Path to the pdf file to scan")
    args = parser.parse_args()
    if args.type == "equity" and not args.first_transaction_type:
        raise ValueError("--first_transaction_type required for equity files.")

    for month, values in parse_account_statement(args.type, args.password, args.file_path, args.first_transaction_type).items():
        print(f"{month} ==> {values}")
    # 11038100