import os
import datetime
import socket
import logging
import threading
import tempfile

import paramiko

from config import config

logger = logging.getLogger(__name__)


class InitSupervisor:
    def __init__(self, project_name, server_list, os_system, superconf_content):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param os_system: 项目所使用的操作系统类型, 比如ubuntu, centos
        :param superconf_name: supervisor的配置文件名称
        :param : superconf_content: supervisor的配置文件内容
        """
        self.deploy_user = "root"
        if os_system == "ubuntu":
            self.supervisor_dir = "/etc/supervisor/conf.d"
            self.supervisor_conf = os.path.join(self.supervisor_dir, "{0}.conf".format(project_name))
        else:
            self.supervisor_dir = "/etc/supervisord.d"
            self.supervisor_conf = os.path.join(self.supervisor_dir, "{0}.ini".format(project_name))
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.local_file = tempfile.NamedTemporaryFile()
        self.supeconf_content = superconf_content
        self.server_list = server_list

    def create_local_file(self):
        self.local_file.write(self.superconf_content)

    def destroy_local_file(self):
        self.local_file.close()

    def init_deploy(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 将本地的临时文件上传到服务器上(已存在会进行覆盖)
            try:
                sftp.put(self.local_file.name, self.supervisor_conf)
            except Exception as e:
                failed[ip] = "配置文件上传失败, 请联系运维!"
                logging.warning("{0}: 配置文件上传失败{1}".format(ip, e))
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
        global failed
        failed = {}
        threads = []
        self.create_local_file()
        for ip in self.server_list:
            t = threading.Thread(target=self.init_deploy, args=(ip,))
            t.start()
            threads.append(t)
        for thread in threads:
            thread.join()
        self.destroy_local_file()
        return failed