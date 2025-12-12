import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-desarrollo'
    
    # CAMBIA ESTA LÍNEA: Reemplaza la URL vieja por la nueva
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'postgresql://yova:j0smlHpbZTp1qgZsruJUHI9XW7Gv9gtt@dpg-d4u0hcfgi27c73a9b4rg-a.virginia-postgres.render.com/sistema_2tdl'
    
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
