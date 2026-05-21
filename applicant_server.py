from ats_app import create_app

app = create_app(enable_applicant=True, enable_employee=False, root_redirect='applicant_home')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False, use_reloader=False)
