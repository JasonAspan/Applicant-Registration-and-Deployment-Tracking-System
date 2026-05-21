from app import app, db

@app.cli.command()
def init_db():
    db.create_all()
    print('Database tables created.')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

