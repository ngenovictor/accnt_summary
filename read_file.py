import argparse
import camelot
import PyPDF2
import pikepdf
import os
import pandas as pd

SUPPORTED_FILE_TYPES = ['safaricom']


def parse_safaricom_statement(password, file_path):
    with pikepdf.open(file_path, password=password) as pdf:
        server_file_path = os.path.join(
            "uploaded_files", 
            os.path.basename(file_path)
            )
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
        all_sum = dict()
        def extract_counts(df_row):
            date = df_row['Completion Time'][:7]
            all_sum.setdefault(date, {'Paid In': 0, 'Withdrawn': 0})
            if df_row['Paid In']:
                all_sum[date]['Paid In'] = all_sum[date]['Paid In'] + float(df_row['Paid In'].replace(',', ''))
            if df_row['Withdrawn']:
                all_sum[date]['Withdrawn'] = all_sum[date]['Withdrawn'] + float(df_row['Withdrawn'].replace(',', ''))

        all_tables.apply(extract_counts, axis=1)

        return all_sum

def parse_account_statement(file_type, password, file_path):
    if file_type == 'safaricom':
        return parse_safaricom_statement(password, file_path)
    else:
        raise NotImplementedError()
    


def is_pdf_file(parser, arg):
    if not str(arg).endswith(".pdf"):
        parser.error(f"The file {arg} is not a pdf!")
    else:
        return arg

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Script to read statement pdf files and give a summary of totals per month.")
    parser.add_argument("--type", choices=SUPPORTED_FILE_TYPES, help=f"Source of the file. Supported are : {SUPPORTED_FILE_TYPES}", required=True)
    parser.add_argument("--password", help="Required for encrypted files. Especially safcom files.")
    parser.add_argument("--file_path", help="Path to the pdf file to scan", type=lambda x: is_pdf_file(parser, x)  ,required=True)
    args = parser.parse_args()
    for month, values in parse_account_statement(args.type, args.password, args.file_path).items():
        print(f"{month} ==> {values}")
    # 11038100