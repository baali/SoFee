import os
import sys
from django.core.wsgi import get_wsgi_application

APP_NAME = 'tweet_d_feed'
os.environ['DJANGO_SETTINGS_MODULE'] = APP_NAME + '.settings'

FILE_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.join(FILE_PATH, "..")

PYTHON_EGG_CACHE_PATH = os.path.join(SITE_ROOT, r'.eggs_cache')

APPS_PATH = os.path.join(FILE_PATH, "..")
# LIB_PATH = os.path.join(SITE_ROOT, r'lib')

sys.path.append(APPS_PATH)
# sys.path.append(LIB_PATH)
application = get_wsgi_application()
