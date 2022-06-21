import multiprocessing
import os
import google.cloud.logging
import yaml
from sanic import Sanic
from sanic.log import logger

google.cloud.logging.Client().setup_logging()

logger.setLevel('INFO')

SANIC_PORT = 5000

app = Sanic(name="Example App")
app.update_config({
    'KEEP_ALIVE': False,
    'ACCESS_LOG': False,
    'REQUEST_TIMEOUT': 90,
    'RESPONSE_TIMEOUT': 90
})

if __name__ == '__main__':
    SANIC_DEBUG = yaml.safe_load(os.getenv('SANIC_DEBUG', 'False'))
    logger.info(f"sanic_debug: {SANIC_DEBUG}")

    worker_count = 1 if SANIC_DEBUG else multiprocessing.cpu_count()
    logger.info(f"Sanic worker_count: {worker_count}")

    app.run(host='0.0.0.0', port=SANIC_PORT, workers=worker_count, debug=SANIC_DEBUG, access_log=False)

# asdfasdf
