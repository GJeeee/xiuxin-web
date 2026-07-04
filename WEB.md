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

## 在线部署（分享给朋友）

本仓库已配置 [Render](https://render.com) 从 GitHub 自动部署。

### 一键开通（只需做一次）

1. 打开：**https://dashboard.render.com/select-repo?type=blueprint**
2. 用 GitHub 登录，选择仓库 **`GJeeee/xiuxin-web`**
3. 点击 **Apply Blueprint** → 等待约 2–5 分钟部署完成
4. 得到公网地址，形如：`https://xiuxin-web.onrender.com` — 发给朋友即可

> 免费档冷启动时首屏可能慢 30–60 秒，属正常现象。

### 自动更新

之后每次 `git push` 到 `main`，Render 会自动重新部署。

若在 Render 控制台创建服务后复制 **Deploy Hook**，可添加到 GitHub 仓库 Secrets（`RENDER_DEPLOY_HOOK`），由 Actions 触发即时部署。

---

## 说明

- 健康相关内容为修心倾向，非医学建议。
- 静态修心路径面板不依赖排盘，可直接阅读全书章节。
