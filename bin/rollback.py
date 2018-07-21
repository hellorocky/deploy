import os
import socket
import logging
import threading

import paramiko

from config import config

logger = logging.getLogger(__name__)


class PHPRollback:
    def __init__(self, project_name, server_list, filename, link_name):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param filename: 构建完成的包的名字, 比如mp-sre-test-15.tar.gz
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        dirname = filename.strip()[:-7]  # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.server_list = server_list
        deploy_tarfile_dir = os.path.join(self.deploy_base_dir, config.DEPLOY_TARFILE_DIR)
        self.remote_tarfile_path = os.path.join(deploy_tarfile_dir, filename)
        self.remote_tardir_path = os.path.join(deploy_tarfile_dir, dirname)
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)
        self.remote_post_script_abspath = os.path.join(self.remote_link_abspath, config.DEPLOY_POST_SCRIPT_NAME)

    def rollback(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path, timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            #  判断要回滚的版本是否存在
            try:
                sftp.stat(self.remote_tarfile_path)
            except Exception as e:
                logger.warning(ip)
                logger.warning(e)
                failed[ip] = "目标文件夹不存在"
                return
            # 做软连
            stdin, stdout, stderr = client.exec_command("ln -sfT {0} {1}".format(self.remote_tardir_path, self.remote_link_abspath),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            out = stdout.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            # 判断是否有回调脚本, 如果有就执行回调脚本
            try:
                sftp.stat(self.remote_post_script_abspath)
                stdin, stdout, stderr = client.exec_command("/bin/bash {0}".format(self.remote_post_script_abspath), timeout=config.CMD_TIMEOUT)
                err = stderr.read()
                out = stdout.read()
                if err:
                    failed[ip] = "回调脚本执行报错: {0}".format(err)
                    logging.warning("{0}回调脚本执行报错: {1}".format(ip, err))
                    return
            except FileNotFoundError:
                logger.info("提示: {0}没有回调脚本!".format(self.project_name))
        except paramiko.AuthenticationException:
            failed[ip] = "SSH认证失败"

        except socket.timeout:
            failed[ip] = "SSH连接超时"
        except Exception as e:
            failed[ip] = "未知错误, 请检查部署系统日志!"
            logging.warning(ip)
            logging.warning(e)
        finally:
            client.close()

    def run(self):
        global failed
        failed = {}
        threads = []
        for ip in self.server_list:
            t = threading.Thread(target=self.rollback, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return failed


class JavaRollback:
    def __init__(self, project_name, server_list, filename, link_name, is_restart):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param filename: 构建完成的包的名字, 比如mp-sre-test-15.tar.gz
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.project_name = project_name
        dirname = filename.strip()[:-7]  # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.server_list = server_list
        self.is_restart = is_restart
        self.link_name = link_name
        deploy_tarfile_dir = os.path.join(self.deploy_base_dir, config.DEPLOY_TARFILE_DIR)
        self.remote_tarfile_path = os.path.join(deploy_tarfile_dir, filename)
        self.remote_tardir_path = os.path.join(deploy_tarfile_dir, dirname)
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)
        self.remote_post_script_abspath = os.path.join(self.remote_link_abspath, config.DEPLOY_POST_SCRIPT_NAME)

    def rollback(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path, timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            #  判断要回滚的版本是否存在
            try:
                sftp.stat(self.remote_tarfile_path)
            except Exception as e:
                logger.warning(ip)
                logger.warning(e)
                failed[ip] = "目标文件夹不存在"
                return
            # 做软连
            stdin, stdout, stderr = client.exec_command("ln -sfT {0} {1}".format(self.remote_tardir_path, self.remote_link_abspath),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            out = stdout.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            # 判断是否需要重启
            if self.is_restart:
                stdin, stdout, stderr = client.exec_command("/usr/bin/supervisorctl restart {0}".format(self.link_name), timeout=config.RESTART_SERVICE_TIMEOUT)
                err = stderr.read()
                out = stdout.read()
                if err:
                    failed[ip] = "部署成功,服务重启失败!"
                    logging.warning("{0}服务重启失败: {1}".format(ip, err))
                    return
        except paramiko.AuthenticationException:
            failed[ip] = "SSH认证失败"

        except socket.timeout:
            failed[ip] = "SSH连接超时"
        except Exception as e:
            failed[ip] = "未知错误, 请检查部署系统日志!"
            logging.warning(ip)
            logging.warning(e)
        finally:
            client.close()

    def run(self):
        global failed
        failed = {}
        threads = []
        for ip in self.server_list:
            t = threading.Thread(target=self.rollback, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return failed