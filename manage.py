import os
import sys
import logging

HOME = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(HOME, "conf"))
sys.path.append(os.path.join(HOME, "bin"))

from bin.utils import create_logger
create_logger()

# 去掉paramiko的info日志
logging.getLogger("paramiko").setLevel(logging.WARNING)

from config import config

from server import app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.PORT, debug=config.DEBUG)
