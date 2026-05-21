from ats_app import create_app

app = create_app(enable_applicant=False, enable_employee=True, root_redirect='employee_home')

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=True, use_reloader=False)
