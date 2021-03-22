from flask import Flask, render_template, request

app = Flask(__name__)
# app.config['UPLOAD_FOLDER'] = '.'

@app.route('/', methods=['GET', 'POST'])
def index():
    account_type_error = ''
    safaricom_password_error = ''
    safaricom_password = ''
    if request.method == 'POST':
        account_type = request.form.get('account-type')
        safaricom_password = request.form.get('safaricom-password')
        statement_file = request.files.get('statement_file')
        if account_type not in ('safaricom', 'coop'):
            account_type_error = "supported account types are safaricom, coop"
        elif account_type == 'safaricom' and not safaricom_password:
            safaricom_password_error = 'Safaricom files require passwords be defined.'
    
    return render_template(
        'index.html', 
        account_type_error=account_type_error,
        safaricom_password=safaricom_password,
    )
