import camelot
from camelot.io import read_pdf
import pandas as pd
import numpy as np


def main(file_path):
    tables = camelot.read_pdf(file_path, pages='all', flavor='stream')
    all_tables = pd.DataFrame()
    for table in tables:
        table_df = table.df
        try:
            table_df = table_df[list(table_df[0]).index('TRANS DATE'):]
        except ValueError:
            continue
        columns = ['_'.join(x.split()) for x in list(table_df.iloc[0])]
        table_df = table_df[1:]
        table_df.columns = columns
        table_df = table_df.replace(r'^\s*$', np.nan, regex=True).dropna(axis=0, subset=['VALUE_DATE'])
        all_tables = all_tables.append(table_df)

    all_sum = dict()
    if all_tables.empty:
        return all_sum

    def extract_counts(df_row):
        date = df_row['VALUE_DATE'][3:].strip()
        all_sum.setdefault(date, {'DEBIT': 0, 'CREDIT': 0})
        credit = float(str(df_row['CREDIT']).replace(',', ''))
        debit = float(str(df_row['DEBIT']).replace(',', ''))
        if not pd.isna(credit):
            all_sum[date]['CREDIT'] = all_sum[date]['CREDIT'] + credit
        if not pd.isna(debit):
            all_sum[date]['DEBIT'] = all_sum[date]['DEBIT'] + debit

    all_tables.apply(extract_counts, axis=1)
    return all_sum
