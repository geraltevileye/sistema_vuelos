import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-desarrollo'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://yova:dt4vax6PavE7pLUXrz80hoZ017Srdx1A@dpg-d4t8guruibrs73cdft8g-a.ohio-postgres.render.com/sistema_gvqe'
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

