# 基于 `apache-libcloud`、`flask`的一个 CMP 管理后端

- `uwsgi` 配置

    配置： `poetry run uwsgi --http 127.0.0.1:5000 --module src.app:app --master --processes 2 --threads 2`
-
