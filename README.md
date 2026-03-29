# novelDownloader

多语言两层架构的小说爬取 & 解析工具。

- **爬虫层（Node.js 20）** — 列表/详情/下载三段 HTTP 采集，输出 txt 文件
- **解析层（Python 3.11）** — 编码检测 + 章节切割 + 写入 MySQL

两层通过共享目录 `data/downloads/` 解耦，各自可独立重启。

---

## 环境要求

| 组件 | 版本 |
|---|---|
| Node.js | ≥ 20 |
| Python | ≥ 3.11 |
| MySQL | 8 |
| Docker + Compose | ≥ 2.0，推荐 |

---

## Docker 快速开始（推荐）

> 需要安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine + Compose 插件。

```bash
# 1. 克隆并进入项目
git clone https://github.com/xyfy/novelDownloader.git
cd novelDownloader

# 2. 复制并填写环境变量
cp .env.example .env
# 编辑 .env：至少填写 DB_PASS

# 3. 一键启动全部服务（MySQL + 爬虫 + 解析层）
docker compose --profile full up --build -d

# 查看运行日志
docker compose --profile full logs -f
```

首次运行会自动构建镜像并初始化 MySQL 表结构（通过 `sql/init.sql`）。

**常用命令：**

```bash
# 仅启动 MySQL（手动运行爬虫/解析层时）
docker compose up mysql -d

# 单独启动解析层
docker compose --profile full up parser -d

# 停止并清理容器（保留数据卷）
docker compose --profile full down

# 停止并同时删除数据卷（重置数据库）
docker compose --profile full down -v
```

---

## 本地手动运行（5 步）

```bash
# 1. 克隆并进入项目
git clone https://github.com/xyfy/novelDownloader.git
cd novelDownloader

# 2. 复制并填写环境变量
cp .env.example .env
# 编辑 .env：填写 DB_PASS 等

# 3. 启动 MySQL（Docker）
docker compose up mysql -d

# 4. 初始化数据库
cd parser
pip install -r requirements.txt
python scripts/init_db.py
cd ..

# 5. 启动爬虫（采集前2页）然后启动解析层
cd crawler && npm install && node index.js --site txt520 --pages 2 &
cd ../parser && python main.py
```

---

## 目录结构

```
novelDownloader/
├── crawler/
│   ├── src/
│   │   ├── core/
│   │   │   ├── scheduler.js       # 通用调度流水线
│   │   │   ├── downloader.js      # 通用下载器（重试、写文件）
│   │   │   ├── db.js              # SQLite 任务去重
│   │   │   ├── siteRegistry.js    # 站点注册表
│   │   │   └── logger.js          # Winston 日志
│   │   └── sites/
│   │       ├── base.js            # BaseSiteAdapter 接口
│   │       ├── txt520.js          # txt520.org 适配器
│   │       └── _template.js       # 新站点模板
│   ├── config.js
│   ├── index.js                   # CLI 入口
│   └── package.json
├── parser/
│   ├── src/
│   │   ├── watcher.py             # 目录轮询 + 流程控制
│   │   ├── encoding_detector.py   # 编码检测
│   │   ├── novel_parser.py        # 章节切割
│   │   ├── text_cleaner.py        # 文本清洗
│   │   └── db_service.py          # MySQL CRUD
│   ├── models/orm.py              # SQLAlchemy ORM
│   ├── scripts/init_db.py         # 建表脚本
│   ├── requirements.txt
│   └── main.py                    # 入口
├── data/downloads/
│   ├── pending/                   # 等待解析
│   ├── processing/                # 解析中
│   ├── done/                      # 已完成
│   └── failed/                    # 失败
├── sql/init.sql                   # MySQL DDL
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 新增站点

1. 复制 `crawler/src/sites/_template.js` 为 `<siteId>.js`
2. 实现 4 个方法：`getListPageUrls` / `parseListPage` / `parseDetailPage` / `parseDownloadPage`
3. 在 `crawler/src/core/siteRegistry.js` 注册
4. 在 `crawler/config.js` 的 `sites` 对象中添加 `seedUrl` 配置

---

## 爬虫 CLI

```bash
# 爬取指定站点的前 N 页
node index.js --site txt520 --pages 10

# 爬取所有页
node index.js --site txt520 --pages all
```

## 解析层 CLI

```bash
# 持续监听 pending/（默认）
python main.py

# 处理完当前 pending/ 后退出
python main.py --once
```

---

## 测试

### 爬虫单元测试（Node.js / Jest）

```bash
cd crawler
npm install
npm test
```

覆盖范围：
- `tests/core/db.test.js` — SQLite 任务 CRUD（upsert / markDone / markFailed / resume）
- `tests/core/downloader.test.js` — 文件下载（大小校验、跳过已存在文件、meta.json 写入）
- `tests/core/siteRegistry.test.js` — 站点注册表（getAdapter / listSites）
- `tests/sites/txt520.test.js` — txt520 适配器（parseListPage / parseDetailPage / parseDownloadPage）

### 解析层单元测试（Python / pytest）

```bash
pip install -r parser/requirements.txt
pytest
```

覆盖范围：
- `parser/tests/test_encoding_detector.py` — UTF-8/BOM/GBK 编码检测
- `parser/tests/test_novel_parser.py` — 章节切割（中文序数 / 数字编号 / 特殊章名 / 无章节兜底）
- `parser/tests/test_text_cleaner.py` — 文本清洗（BOM 去除 / 换行规范化 / 广告过滤 / 空行折叠）

---



**Q: 编码检测不准**
chardet 对 GB2312/GBK 混合文件有时置信度低。`encoding_detector.py` 已内置枚举兜底，顺序为 `utf-8-sig → utf-8 → gbk → gb2312 → big5`。

**Q: 章节识别不准**
`novel_parser.py` 使用三组正则，自动选命中率最高的。若有问题，检查正则是否覆盖该书的章节格式并提 Issue。

**Q: IP 被封**
- 每次请求等待随机延迟（默认 3–10 秒），同时轮换 User-Agent，模拟真实浏览器行为。
- 并发默认 2（`CRAWLER_CONCURRENCY=2`）
- 如遇封锁，可增大间隔或减小并发：
  ```bash
  CRAWLER_REQUEST_INTERVAL_MS=5000      # 最短等待 5 秒
  CRAWLER_REQUEST_INTERVAL_MAX_MS=15000 # 最长等待 15 秒
  CRAWLER_CONCURRENCY=1
  ```
- 如需使用代理（HTTP/HTTPS），在 `.env` 中设置：
  ```bash
  CRAWLER_PROXY=http://user:pass@proxy.example.com:8080
  ```

**Q: 中断后如何续跑**
直接重新运行命令即可。爬虫通过 SQLite `crawler_tasks` 表记录状态；解析层通过 MySQL `parse_status` 字段跳过已处理的书。

---

## 数据库表

| 表 | 用途 |
|---|---|
| `books` | 书籍元数据 + 解析状态 |
| `chapters` | 章节正文（LONGTEXT）|
| `parse_logs` | 解析过程日志 |
