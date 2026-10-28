from project.app import app, db
from project.models import Post

with app.app_context():
    db.create_all()
    db.session.commit()
