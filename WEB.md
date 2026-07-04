# 修心网页

Vue 3 + Tailwind 单页应用，Flask 提供排盘与修心建议 API；含《王凤仪性命哲学浅述》完整修心路径（按原书五篇逐章展开）。

## 本地运行

```bash
pip install -r requirements.txt
WEB_PORT=8766 python3 web_app.py
```

浏览器打开：http://127.0.0.1:8766/

## 目录

| 路径 | 说明 |
|------|------|
| `web/static/index.html` | 前端 SPA |
| `web/static/data/wangfengyi-path.json` | 王凤仪全书章节数据 |
| `web_app.py` | Flask 服务 |
| `xiuxing_engine.py` | 命盘 → 修心文案 |
| `paipan.py` | 排盘引擎 |

## 说明

- 健康相关内容为修心倾向，非医学建议。
- 静态修心路径面板不依赖排盘，可直接阅读全书章节。
