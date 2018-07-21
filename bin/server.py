import json
import logging

from flask import Flask, Response, request
from prometheus_client import multiprocess
from prometheus_client import generate_latest, CollectorRegistry, CONTENT_TYPE_LATEST, Counter, Histogram

from config import config

from init_deploy import InitSupervisor
from deploy import PHPDeploy, JavaDeploy, GolangDeploy
from get_current_version import JavaGetCurrentVersion, PHPGetCurrentVersion
from rollback import PHPRollback, JavaRollback
from get_latest_log import JavaGetLatestLog, PHPGetLatestLog

logger = logging.getLogger(__name__)

app = Flask(__name__)

REQUEST_COUNTER = Counter("request_processing_counter", "接口调用计数器",  ["interface"])

REQUEST_HISTOGRAM = Histogram('response_latency_seconds', 'Response latency (seconds)', ["interface"])
DEPLOY_REQUEST_HISTOGRAM = REQUEST_HISTOGRAM.labels(interface="/deploy")
ROLLBACK_REQUEST_HISTOGRAM = REQUEST_HISTOGRAM.labels(interface="/rollback")


@app.route("/init_deploy", methods=["POST"])
@DEPLOY_REQUEST_HISTOGRAM.time()
def init_deploy():
    if request.method == "POST":
        REQUEST_COUNTER.labels(interface="/init_deploy").inc()
        # 安全校验
        if request.remote_addr not in config.IP_WHITE_LIST:
            return json.dumps({"status_code": 403, "data": "不允许的客户端IP: {0}".format(request.remote_addr)})
        if request.headers.get("APP_TOKEN") not in config.APP_TOKEN:
            return json.dumps({"status_code": 401, "data": "未认证的请求!"})
        # 获取并校验参数
        data = request.get_json()
        logger.info(json.dumps(data))
        project_name = data.get("project_name")  # 项目名称
        server_list = data.get("server_list")  # 要部署的服务器IP列表
        language = data.get("language")  # 项目所使用的编程语言
        os_system = data.get("os_system", "centos")  # 软连接的名称
        superconf_content = data.get("superconf_content")  # 项目的supervisor配置文件

        if not all([project_name, server_list, superconf_content]):
            return json.dumps({"status_code": 404, "data": "参数缺失"})
        if language.lower() in ["java", "go"]:
            init_supervisor = InitSupervisor(project_name, server_list, os_system, superconf_content)
            result = init_supervisor.run()
        else:
            return json.dumps({"status_code": 405, "data": "Not supported!"})
        if result:
            return json.dumps({"status_code": 501, "data": result})
        return json.dumps({"status_code": 200, "data": "初始化成功"})


@app.route("/deploy", methods=["POST"])
@DEPLOY_REQUEST_HISTOGRAM.time()
def deploy():
    if request.method == "POST":
        REQUEST_COUNTER.labels(interface="/deploy").inc()

        # 安全校验
        if request.remote_addr not in config.IP_WHITE_LIST:
            return json.dumps({"status_code": 403, "data": "不允许的客户端IP: {0}".format(request.remote_addr)})
        if request.headers.get("APP_TOKEN") not in config.APP_TOKEN:
            return json.dumps({"status_code": 401, "data": "未认证的请求!"})
        # 获取并校验参数
        data = request.get_json()
        logger.info(json.dumps(data))
        project_name = data.get("project_name")  # 项目名称
        link_name = data.get("link_name")  # 软连接的名称
        server_list = data.get("server_list")  # 要部署的服务器IP列表
        file_url = data.get("file_url")  # 构建好的包的OSS地址
        filename = data.get("filename")  # 包名字, 包含tar.gz
        filename_delete = data.get("filename_delete") or "test.tgz" # 待删除的包名字, 包含tar.gz
        language = data.get("language")  # 项目所使用编程语言
        is_restart = data.get("is_restart", False)  # 部署完以后是否重启

        if not all([project_name, link_name, server_list, file_url, filename, language]):
            return json.dumps({"status_code": 404, "data": "参数缺失"})
        if language.lower() == "php":
            deploy = PHPDeploy(project_name, server_list, file_url, filename, link_name, filename_delete)
            result = deploy.run()
        elif language.lower() == "java":
            deploy = JavaDeploy(project_name, server_list, file_url, filename, link_name, filename_delete, is_restart)
            result = deploy.run()
        else:
            return json.dumps({"status_code": 405, "data": "Not supported!"})
        if result:
            return json.dumps({"status_code": 501, "data": result})
        return json.dumps({"status_code": 200, "data": "部署成功"})


@app.route("/rollback", methods=["POST"])
@ROLLBACK_REQUEST_HISTOGRAM.time()
def rollback():
    if request.method == "POST":
        REQUEST_COUNTER.labels(interface="/rollback").inc()
        # 获取并校验参数
        data = request.get_json()
        logger.info(json.dumps(data))
        project_name = data.get("project_name")  # 项目名称
        link_name = data.get("link_name")  # 软连接的名称
        language = data.get("language")  # 项目所使用编程语言
        server_list = data.get("server_list")  # 要部署的服务器IP列表
        filename = data.get("filename")  # 包名字
        is_restart = data.get("is_restart", False)  # 部署完以后是否重启

        if not all([project_name, link_name, language, server_list, filename]):
            return json.dumps({"status_code": 404, "data": "参数缺失"})

        if language.lower() == "php":
            rollback = PHPRollback(project_name, server_list, filename, link_name)
            result = rollback.run()
        elif language.lower() == "java":
            rollback = JavaRollback(project_name, server_list, filename, link_name, is_restart)
            result = rollback.run()
        else:
            return json.dumps({"status_code": 405, "data": "Not supported!"})
        if result:
            return json.dumps({"status_code": 501, "data": json.dumps(result)})
        return json.dumps({"status_code": 200, "data": "回滚成功!"})


@app.route("/get_current_version", methods=["GET"])
@ROLLBACK_REQUEST_HISTOGRAM.time()
def get_current_version():
    if request.method == "GET":
        REQUEST_COUNTER.labels(interface="/get_current_version").inc()
        # 获取并校验参数
        project_name = request.args.get("project_name")  # 项目名称
        link_name = request.args.get("link_name")  # 软连接的名称
        language = request.args.get("language")  # 项目所使用编程语言
        server_list = request.args.get("server_list")  # 要部署的服务器IP列表

        if not all([project_name, link_name, language, server_list]):
            return json.dumps({"status_code": 404, "data": "参数缺失"})

        server_list = server_list.split(",")
        server_list = [ip.strip() for ip in server_list]

        if language.lower() == "php":
            get_cur_version = PHPGetCurrentVersion(project_name, server_list, link_name)
            result = get_cur_version.run()
        elif language.lower() == "java":
            get_cur_version = JavaGetCurrentVersion(project_name, server_list, link_name)
            result = get_cur_version.run()
        else:
            return json.dumps({"status_code": 405, "data": "Not supported!"})
        return json.dumps({"status_code": 200, "data": result})


@app.route("/get_latest_log", methods=["GET"])
@ROLLBACK_REQUEST_HISTOGRAM.time()
def get_latest_log():
    if request.method == "GET":
        REQUEST_COUNTER.labels(interface="/get_latest_log").inc()
        # 获取并校验参数
        project_name = request.args.get("project_name")  # 项目名称
        logname = request.args.get("logname")  # 日志名称(info.log, err.log)
        language = request.args.get("language")  # 项目所使用编程语言
        server_list = request.args.get("server_list")  # 要部署的服务器IP列表
        line = request.args.get("line")  # 要查看后面多少行的日志
        logger.info(json.dumps(request.args))

        if not all([project_name, logname, language, server_list, line]):
            return json.dumps({"status_code": 404, "data": "参数缺失"})
        if not line.isdigit():
            return json.dumps({"status_code": 400, "data": "行数必须是数字"})
        line = int(line)
        if line > 1000:
            return json.dumps({"status_code": 501, "data": "最多查看1000行日志"})

        server_list = server_list.split(",")
        server_list = [ip.strip() for ip in server_list]

        if language.lower() == "php":
            get_latest_log = PHPGetLatestLog(project_name, server_list, logname, line)
            result = get_latest_log.run()
        elif language.lower() == "java":
            get_latest_log = JavaGetLatestLog(project_name, server_list, logname, line)
            result = get_latest_log.run()
        else:
            return json.dumps({"status_code": 405, "data": "Not supported!"})
        return json.dumps({"status_code": 200, "data": result})


@app.route("/metrics")
def prometheus_metrics():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    data = generate_latest(registry)
    return Response(data, mimetype=CONTENT_TYPE_LATEST)
