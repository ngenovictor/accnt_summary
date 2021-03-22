import argparse

SUPPORTED_FILE_TYPES = ['safaricom']


def parse_safaricom_statement(password, file_path):
    return {"2021-01": {"In": 0, "Out": 0}}

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