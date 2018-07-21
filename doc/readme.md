#### 服务介绍

&emsp;部署服务, 用于将上一个环节构建完成的包同步到目标服务器并替换目标软连接, 并支持回滚.

#### 服务地址

`http://deploy.office.bbobo.com`

#### 部署

* 接口

`/deploy`

* 请求方式

`POST`

* 请求参数

```
{
        "project_name": "mp-sre-platform",
        "link_name": "zeus",
        "server_list": ["192.168.210.3"],
        "file_url": "http://mp-devops-oss.oss-cn-beijing-internal.aliyuncs.com/mp-sre-devops/zeus-0.1.1.tar.gz",
        "filename": "zeus-0.1.1.tar.gz",
        "filename_delete": "zeus-0.1.0.tar.gz", # 可选参数
        "language": "php",
        "is_restart": False, # 是否重启, 仅适用于Java项目, 默认不重启
        "deploy_dir": "profile" # 要部署的目录, 只用于golang项目, 比如, 部署目录为/opt/profile, 传profile即可
        }
```

* 返回实例

部署成功的话:

```
{"status_code": 200, "data": "部署成功!"}
```

部署失败的话:

```
{"status_code": 501, "data": {"192.168.210.3": "SSH连接失败", "192.168.1.1": "下载文件失败"}}
```

#### 回滚

* 接口

`/rollback`

* 请求方式

`POST`

* 请求参数

```
{
        "project_name": "mp-sre-platform",
        "link_name": "zeus",
        "server_list": ["192.168.210.3"],
        "filename": "zeus-0.1.1.tar.gz",
        "language": "php",
        "is_restart": False, # 是否重启, 仅适用于Java项目, 默认不重启
        "deploy_dir": "profile"
        }
```

* 返回实例

回滚成功的话:

```
{"status_code": 200, "data": "回滚成功!"}
```

回滚失败的话:

```
{"status_code": 501, "data": {"192.168.210.3": "SSH连接失败", "192.168.1.1": "下载文件失败"}}
```

#### 检查版本

* 接口

`/get_current_version`

* 请求方式

`GET`

* 请求参数

```
/get_current_version?project_name=mp-sre-eureka-test&language=java&link_name=eureka&server_list=192.168.210.10,192.168.1.1&deploy_dir=profile
```

* 返回实例


```
{
    "status_code": 200,
    "data": {
	    "succeed": {
		    "192.168.1.1": "mp-media-wide-api-service-v20180630165728-105.jar",
		    "192.168.1.2": "mp-media-wide-api-service-v20180630165728-104.jar"
	    },
	    "failed": {
		    "192.168.1.3": "SSH认证失败"
	    }
    }
}
```

#### 初始化部署

新项目批量配置supervisor的配置文件.

* 接口

`/init_deploy`

* 请求方式

`POST`

* 请求参数

```
{
        "project_name": "mp-sre-platform",
        "server_list": ["192.168.210.3"],
        "language": "java",
        "os_system": "centos",  # 暂时不传, 后期备用(centos, ubuntu)
        "superconf_content": "supervisor的配置文件字符串"
        }
```

* 返回实例

成功的话:

```
{"status_code": 200, "data": "初始化成功!"}
```

失败的话:

```
{"status_code": 501, "data": {"192.168.210.3": "SSH连接失败", "192.168.1.1": "下载文件失败"}}
```


#### 查看日志

* 接口

`/get_latest_log`

* 请求方式

`GET`

* 请求参数

```
{
        "project_name": "mp-sre-platform",
        "server_list": ["192.168.210.3"],
        "logname": "info.log", # 只能是info.log, warning.log, error.log
        "language": "java",
        "line": 12, # 要查看的行数(<1000)
        }
```

* 返回实例


```
{
    "status_code": 200,
    "data": {
	    "succeed": {
		    "192.168.1.1": "A\nb\n",
		    "192.168.1.2": "A\nb\n"
	    },
	    "failed": {
		    "192.168.1.3": "SSH认证失败"
	    }
    }
}
```
