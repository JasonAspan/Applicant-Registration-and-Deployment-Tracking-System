from ats_app import create_app, db

app = create_app(enable_applicant=True, enable_employee=True, root_redirect='applicant_home')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

