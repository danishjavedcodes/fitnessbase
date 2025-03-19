from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import login_manager
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        "postgresql://postgres:wmepPSOcLBehjMxScBFsxCbnPVEfcUIQ@caboose.proxy.rlwy.net:34585/railway"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask-Login configuration
    SESSION_PROTECTION = 'strong'
    
    # Bcrypt configuration
    BCRYPT_LOG_ROUNDS = 12


db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Import and register blueprints here
    # from .routes import main
    # app.register_blueprint(main)

    return app