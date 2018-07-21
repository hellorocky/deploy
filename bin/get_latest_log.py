import os
import datetime
import socket
import logging
import threading

import paramiko

from config import config

logger = logging.getLogger(__name__)


class JavaGetLatestLog:
    def __init__(self, project_name, server_list, filename, line):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param filename: 要查看的log文件名称
        :param line: 查看的行数
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/log"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        self.logpath = os.path.join(self.deploy_base_dir, filename)
        self.server_list = server_list
        self.line = line

    def check(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 判断日志文件是否存在
            try:
                sftp.stat(self.logpath)
            except:
                failed[ip] = "日志文件不存在, 请将业务日志打到: {0}".format(self.deploy_base_dir)
                return
            stdin, stdout, stderr = client.exec_command("tail -{0} {1}".format(self.line, self.logpath), timeout=config.CMD_TIMEOUT)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if err:
                failed[ip] = "读取日志失败, 请联系运维!"
                logger.warning("{0}: 读取日志失败: {1}".format(ip, err))
                return
            succeed[ip] = out
        except paramiko.AuthenticationException:
            failed[ip] = "SSH认证失败"

        except socket.timeout:
            failed[ip] = "SSH连接超时"
        except Exception as e:
            failed[ip] = "未知错误, 请检查部署系统日志!"
            logger.warning("{0}: {1}".format(ip, e))
        finally:
            client.close()

    def run(self):
        global failed, succeed
        failed, succeed = {}, {}
        threads = []
        for ip in self.server_list:
            t = threading.Thread(target=self.check, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return {"succeed": succeed, "failed": failed}


class PHPGetLatestLog:
    def __init__(self, project_name, server_list, filename, line):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param filename: 要查看的log文件名称
        :param line: 查看的行数
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/log"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        self.logpath = os.path.join(self.deploy_base_dir, filename)
        self.server_list = server_list
        self.line = line

    def check(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 判断日志文件是否存在
            try:
                sftp.stat(self.logpath)
            except:
                failed[ip] = "日志文件不存在, 请将业务日志打到: {0}".format(self.deploy_base_dir)
                return
            stdin, stdout, stderr = client.exec_command("tail -{0} {1}".format(self.line, self.logpath), timeout=config.CMD_TIMEOUT)
            out = stdout.read().decode()
            err = stderr.read().decode()
            if err:
                failed[ip] = "读取日志失败, 请联系运维!"
                logger.warning("{0}: 读取日志失败: {1}".format(ip, err))
                return
            succeed[ip] = out
        except paramiko.AuthenticationException:
            failed[ip] = "SSH认证失败"

        except socket.timeout:
            failed[ip] = "SSH连接超时"
        except Exception as e:
            failed[ip] = "未知错误, 请检查部署系统日志!"
            logger.warning("{0}: {1}".format(ip, e))
        finally:
            client.close()

    def run(self):
        global failed, succeed
        failed, succeed = {}, {}
        threads = []
        for ip in self.server_list:
            t = threading.Thread(target=self.check, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return {"succeed": succeed, "failed": failed}