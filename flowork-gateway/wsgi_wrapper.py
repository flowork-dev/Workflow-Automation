#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-gateway\wsgi_wrapper.py JUMLAH BARIS 16 
#######################################################################

from uvicorn.middleware.wsgi import WSGIMiddleware
from app import create_app
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Initializing Flask application via create_app()...")
flask_app = create_app()
logger.info("Wrapping Flask app with WSGIMiddleware for Uvicorn.")
application = WSGIMiddleware(flask_app)
