# 部署相关说明

## Python虚拟环境

初始化

```shell
python3 -m venv flask
```

进入虚拟环境

```shell
source flask/bin/activate
```

## 数据库生成/修改（虚拟环境内）

```shell
flask db migrate -m ""
flask db upgrade
```

## gunicorn部署（虚拟环境内）

```shell
gunicorn -w 1 -k gevent --worker-connections 10 -b 0.0.0.0:5000 cloud_platform:app
```

部署为守护进程

```shell
gunicorn -w 1 -k gevent --worker-connections 10 -b 0.0.0.0:5000 --daemon cloud_platform:app
```

