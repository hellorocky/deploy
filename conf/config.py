import os


class Config(object):
    # 服务监听端口
    PORT = 80

    # 允许连接的客户端IP, 防止未识别的机器连接
    IP_WHITE_LIST = ["192.168.1.1", "192.168.1.2"]

    # APP Token, 给每个允许的调用签发的token, 方便识别不同的请求
    APP_TOKEN = {
        "kOsdsd": "APPa",
        "FD12fj": "APPb",
    }

    # 目标机缓存目录, 放历史版本的项目文件和文件夹
    DEPLOY_TARFILE_DIR = ".deploy"
    DEPLOY_POST_SCRIPT_NAME = "____post-deploy.sh"
    # 操作超时时间(秒)
    SSH_TIMEOUT = 90
    CMD_TIMEOUT = 90
    RESTART_SERVICE_TIMEOUT = 90
    # 日志文件路径
    LOG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log", "app.log")


class ProductionConfig(Config):
    # 日志配置
    LOG_LEVEL = "INFO"
    DEBUG = False


class DevelopmentConfig(Config):
    LOG_LEVEL = "DEBUG"
    DEBUG = True


config = ProductionConfig
