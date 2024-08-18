from app import create_app
from app.models import db

app = create_app()
@app.cli.command('drop-db')
def drop_db():
    """Drops all tables in the database."""
    db.drop_all()
    print("Dropped all tables.")

@app.cli.command('create-db')
def create_db():
    """Creates all tables in the database."""
    db.create_all()
    print("Created all tables.")

@app.cli.command('reinitialize-db')
def reinitialize_db():
    """Drops and recreates all tables in the database."""
    db.drop_all()
    print("Dropped all tables.")
    db.create_all()
    print("Created all tables.")

if __name__ == '__main__':
    
    app.run(debug=True)