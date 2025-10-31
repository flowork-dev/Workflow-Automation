#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\app\config.py JUMLAH BARIS 19 
#######################################################################

import os
from dotenv import load_dotenv
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(basedir, ".env")) # Muat .env dari root gateway
class Config:
    """
    Kelas konfigurasi utama untuk aplikasi Flask (Gateway).
    (MODIFIED FASE 3) Disederhanakan untuk SQLite dan tanpa Redis.
    """
    SECRET_KEY = os.getenv("JWT_SECRET_KEY") or "you-should-really-change-this-in-production" # English Hardcode
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or "sqlite:////app/data/gateway.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
