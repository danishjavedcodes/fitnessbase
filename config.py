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