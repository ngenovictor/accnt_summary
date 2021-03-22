from flask import Flask, render_template, request
import read_file
import io
import os


app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = '.'

@app.route('/', methods=['GET', 'POST'])
def index():
    account_type_error = ''
    safaricom_password_error = ''
    safaricom_password = ''
    statement_file_errors = ''
    results = None
    if request.method == 'POST':
        account_type = request.form.get('account-type')
        safaricom_password = request.form.get('safaricom-password')
        statement_file = request.files.get('statement-file')
        if statement_file is None or not statement_file.filename:
            statement_file_errors = "Could not upload file. Refresh page and attach again."
        elif not statement_file.filename.endswith('.pdf'):
            statement_file_errors = "Only pdf files supported"
        elif account_type not in ('safaricom', 'coop'):
            account_type_error = "supported account types are safaricom, coop"
        elif account_type == 'safaricom' and not safaricom_password:
            safaricom_password_error = 'Safaricom files require passwords be defined.'
        else:
            file_path = os.path.join('uploaded_files', os.path.basename(statement_file.filename))
            statement_file.save(file_path) # upload file
            results = read_file.parse_account_statement(
                account_type, safaricom_password, file_path)
            os.remove(file_path)

    return render_template(
        'index.html', 
        account_type_error=account_type_error,
        safaricom_password=safaricom_password,
        statement_file_errors=statement_file_errors,
        results=results,
    )
