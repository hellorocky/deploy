import os
import socket
import logging
import threading

import paramiko

from config import config

logger = logging.getLogger(__name__)


class JavaGetCurrentVersion:
    def __init__(self, project_name, server_list, link_name):
        """
        :param project_name: 项目名称, 比如mp-sre-platform
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        self.link_name = link_name
        self.server_list = server_list
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)

    def get(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 创建存放压缩包的文件夹, 如果有就跳过
            try:
                path = sftp.readlink(self.remote_link_abspath)
                succeed[ip] = os.path.basename(path)
            except FileNotFoundError:
                failed[ip] = "软连接不存在!"
            except Exception as e:
                logger.error(e)
                failed[ip] = "读取软连接失败!"
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
            t = threading.Thread(target=self.get, args=(ip,))
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
        return {"succeed": succeed, "failed": failed}


class PHPGetCurrentVersion:
    def __init__(self, project_name, server_list, link_name):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        self.link_name = link_name
        self.server_list = server_list
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)

    def get(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 创建存放压缩包的文件夹, 如果有就跳过
            try:
                path = sftp.readlink(self.remote_link_abspath)
                succeed[ip] = os.path.basename(path)
            except FileNotFoundError:
                failed[ip] = "软连接不存在!"
            except Exception as e:
                logger.error(e)
                failed[ip] = "读取软连接失败!"
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
            t = threading.Thread(target=self.get, args=(ip,))
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
        return {"succeed": succeed, "failed": failed}