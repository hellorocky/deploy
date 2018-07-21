"""gunicorn WSGI server configuration, used for production environment"""

bind = "0.0.0.0:80"
max_requests = 1000 # 当某个worker同时处理超过1000的时候会重启,防止内存泄漏
worker_class = 'sync'
workers = 4
worker_connections = 100 # 同时允许最大100个连接
keepalive = 300 # HTTP的keepalive, 等待下一个请求的时间, 如果30秒没有下一次请求就会关闭这个HTTP连接
timeout = 300 # 子进程30秒内没有响应那么主进程会杀死他然后起一个新的子进程


def worker_exit(server, worker):
    from prometheus_client import multiprocess
    multiprocess.mark_process_dead(worker.pid)
