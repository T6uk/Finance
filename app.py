# app.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
# Import models
from models import *

# Import routes
from routes.auth import *
from routes.dashboard import *
from routes.expense import *
from routes.income import *
from routes.budget import *
from routes.category import *
from routes.recurring import *
from routes.savings import *
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///money_manager.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Add context processor to make now() available in templates
@app.context_processor
def utility_processor():
    return {'now': datetime.now}


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)