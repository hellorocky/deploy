import os
import datetime
import socket
import logging
import threading

import paramiko

from config import config

logger = logging.getLogger(__name__)


class PHPDeploy:
    def __init__(self, project_name, server_list, file_url, filename, link_name, filename_delete):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param file_url: http://xxx/mp-sre-test-15.tar.gz
        :param filename: 构建完成的包的名字, 比如mp-sre-test-15.tar.gz
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.file_url = file_url
        self.project_name = project_name
        self.filename = filename
        self.filename_delete = filename_delete
        self.dirname = filename.strip()[:-7]  # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.dirname_delete = filename_delete.strip()[:-7] if filename_delete else "test" # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.server_list = server_list
        self.deploy_tarfile_dir = os.path.join(self.deploy_base_dir, config.DEPLOY_TARFILE_DIR)
        self.remote_tarfile_path = os.path.join(self.deploy_tarfile_dir, filename)
        self.remote_tardir_path = os.path.join(self.deploy_tarfile_dir, self.dirname)
        self.remote_tarfile_path_delete = os.path.join(self.deploy_tarfile_dir, filename_delete)
        self.remote_tardir_path_delete = os.path.join(self.deploy_tarfile_dir, self.dirname_delete)
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.remote_tarfile_path_tmp = os.path.join(self.deploy_tarfile_dir, filename + ts)
        self.remote_tardir_path_tmp = os.path.join(self.deploy_tarfile_dir, self.dirname + ts)
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)
        self.remote_post_script_abspath = os.path.join(self.remote_link_abspath, config.DEPLOY_POST_SCRIPT_NAME)

    def deploy(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 创建存放压缩包的文件夹, 如果有就跳过
            try:
                sftp.mkdir(self.deploy_tarfile_dir)
            except OSError:
                pass
            # 如果存在相同名字的文件或者文件夹会mv了
            try:
                sftp.stat(self.remote_tarfile_path)
                sftp.posix_rename(self.remote_tarfile_path, self.remote_tarfile_path_tmp)
                sftp.posix_rename(self.remote_tardir_path, self.remote_tardir_path_tmp)
            except:
                pass
            # 下载要部署的包文件到目标路径
            stdin, stdout, stderr = client.exec_command("cd {0};wget -q {1}".format(self.deploy_tarfile_dir, self.file_url),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            out = stdout.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            # 解压缩
            stdin, stdout, stderr = client.exec_command("tar -zxf {0} -C {1}".format(self.remote_tarfile_path, self.deploy_tarfile_dir),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            out = stdout.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            # 做软连
            stdin, stdout, stderr = client.exec_command("ln -sfvT {0} {1}".format(self.remote_tardir_path, self.remote_link_abspath),
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
            # 判断是否有要删除的历史文件, 有的话删除, 没有的话跳过
            try:
                if self.filename_delete:
                    sftp.remove(self.remote_tarfile_path_delete)
                    sftp.rmdir(self.remote_tardir_path_delete)
            except Exception as e:
                logger.warning("{0}: 删除旧版本失败!".format(ip))
                logger.warning(e)
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
            t = threading.Thread(target=self.deploy, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return failed


class JavaDeploy:
    def __init__(self, project_name, server_list, file_url, filename, link_name, filename_delete, is_restart):
        """
        :param project_name: 项目名称, 比如mp-sre-test
        :param server_list: ["192.168.1.1", "192.168.1.2"]
        :param file_url: http://xxx/mp-sre-test-15.tar.gz
        :param filename: 构建完成的包的名字, 比如mp-sre-test-15.tar.gz
        :param link_name: 软连接的名称
        """
        self.deploy_user = "root"
        self.deploy_base_dir = "/root/service"
        self.private_key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "conf", "id_rsa_root")
        self.file_url = file_url
        self.project_name = project_name
        self.link_name = link_name
        self.filename = filename
        self.is_restart = is_restart
        self.filename_delete = filename_delete
        self.dirname = filename.strip()[:-7]  # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.dirname_delete = filename_delete.strip()[:-7] if filename_delete else "test" # 解压缩后的文件夹名称, 这里只是去掉了.tar.gz
        self.server_list = server_list
        self.deploy_tarfile_dir = os.path.join(self.deploy_base_dir, config.DEPLOY_TARFILE_DIR)
        self.remote_tarfile_path = os.path.join(self.deploy_tarfile_dir, filename)
        self.remote_tardir_path = os.path.join(self.deploy_tarfile_dir, self.dirname)
        self.remote_tarfile_path_delete = os.path.join(self.deploy_tarfile_dir, filename_delete)
        self.remote_tardir_path_delete = os.path.join(self.deploy_tarfile_dir, self.dirname_delete)
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.remote_tarfile_path_tmp = os.path.join(self.deploy_tarfile_dir, filename + ts)
        self.remote_tardir_path_tmp = os.path.join(self.deploy_tarfile_dir, self.dirname + ts)
        self.remote_link_abspath = os.path.join(self.deploy_base_dir, link_name)
        self.remote_post_script_abspath = os.path.join(self.remote_link_abspath, config.DEPLOY_POST_SCRIPT_NAME)

    def deploy(self, ip):
        try:
            # 连接远程服务器
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(ip.strip(), 22, self.deploy_user, key_filename=self.private_key_path,timeout=config.SSH_TIMEOUT)
            # 构造sftp用于操作远程的目录
            sftp = paramiko.SFTPClient.from_transport(client.get_transport())
            # 创建存放压缩包的文件夹, 如果有就跳过
            try:
                sftp.mkdir(self.deploy_tarfile_dir)
            except OSError:
                pass
            # 如果存在相同名字的文件或者文件夹会mv了
            try:
                sftp.stat(self.remote_tarfile_path)
                sftp.posix_rename(self.remote_tarfile_path, self.remote_tarfile_path_tmp)
                sftp.posix_rename(self.remote_tardir_path, self.remote_tardir_path_tmp)
            except:
                pass
            # 下载要部署的包文件到目标路径
            stdin, stdout, stderr = client.exec_command("cd {0};wget -q {1}".format(self.deploy_tarfile_dir, self.file_url),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            try:
                sftp.stat(self.remote_tarfile_path)
            except Exception as e:
                logger.warning("{0}: {1}".format(ip, e))
                failed[ip] = "文件下载失败"
                return
            # 解压缩
            stdin, stdout, stderr = client.exec_command("tar -zxf {0} -C {1}".format(self.remote_tarfile_path, self.deploy_tarfile_dir),
                                                        timeout=config.CMD_TIMEOUT)
            err = stderr.read()
            if err:
                failed[ip] = "{0}".format(err)
                logging.warning("{0}: {1}".format(ip, err))
                return
            # 做软连接
            try:
                sftp.remove(self.remote_link_abspath)
            except:
                pass
            try:
                sftp.symlink(self.remote_tardir_path, self.remote_link_abspath)
            except Exception as e:
                logger.warning("{0}: 制作软连接失败: {1}".format(ip, e))
                return
            # 判断是否需要重启
            if self.is_restart:
                stdin, stdout, stderr = client.exec_command("/usr/bin/supervisorctl update;/usr/bin/supervisorctl restart {0}".format(self.link_name), timeout=config.RESTART_SERVICE_TIMEOUT)
                err = stderr.read()
                if err:
                    failed[ip] = "部署成功,服务重启失败!"
                    logging.warning("{0}: 服务重启失败: {1}".format(ip, err))
                    return
            # 判断是否有要删除的历史文件, 有的话删除, 没有的话跳过
            if self.filename_delete:
                try:
                    sftp.remove(self.remote_tarfile_path_delete)
                    sftp.rmdir(self.remote_tardir_path_delete)
                except Exception as e:
                    logger.warning("{0}: 删除旧版本失败: {1}".format(ip, e))
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
        for ip in self.server_list:
            t = threading.Thread(target=self.deploy, args=(ip,))
            t.start()
            threads.append(t)
            logging.debug("{0} thread start!".format(ip))
        for thread in threads:
            thread.join()
        return failed
