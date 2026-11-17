# RAGMind 启动与使用说明

> 本文档基于尚硅谷《掌柜智库》教案整理，适配本机（Windows 11 + Docker Desktop + MinIO exe + conda `knowledge` 环境）。

---

## 一、启动顺序（三步）

### 第 1 步：一键启动（推荐）

直接双击项目根目录的 **`启动.bat`**，它会自动完成：

| 顺序 | 动作 | 说明 |
|------|------|------|
| 1 | 启动 Docker Desktop 引擎 | 若引擎未运行，自动拉起并等待就绪（最多 120 秒） |
| 2 | `docker compose up -d` | 启动 etcd / Milvus / Attu / Neo4j / MongoDB 五个容器 |
| 3 | 启动 MinIO（独立 exe） | `minio.exe server D:\minio-data --address :9000 --console-address :9001` |
| 4 | 启动两个 Python 服务 | 导入服务（:8000）+ 问答服务（:8001），均用 conda `knowledge` 环境 |
| 5 | 打开两个页面 | 自动打开导入页与问答页 |

脚本是幂等的：已运行的容器/进程会跳过，不会重复启动。

### 第 2 步：手动启动（不双击脚本时）

```powershell
# 1. 打开 Docker Desktop，等待引擎变绿

# 2. 拉容器（仅首次；之后 Docker Desktop 会自动重启容器）
cd D:\Desktop\PythonProject
docker compose up -d

# 3. 启动 MinIO（每次开机都要，Docker 不代管）
Start-Process -FilePath "D:\Desktop\PythonProject\minio.exe" `
  -ArgumentList "server","D:\minio-data","--address",":9000","--console-address",":9001" `
  -WindowStyle Hidden

# 4. 启动两个服务（conda knowledge 环境）
D:\Dev\Anaconda\envs\knowledge\python.exe -m app.import_process.api.file_import_service
D:\Dev\Anaconda\envs\knowledge\python.exe -m app.query_process.api.query_service
```

### 第 3 步：验证是否全部就绪

```powershell
# 容器状态
docker ps

# 健康检查
Invoke-WebRequest -Uri 'http://localhost:9091/healthz'      # Milvus → {"ok":true}
Invoke-WebRequest -Uri 'http://localhost:9000/minio/health/live'   # MinIO → 200
Invoke-WebRequest -Uri 'http://127.0.0.1:8000/docs'          # 导入 → 200
Invoke-WebRequest -Uri 'http://127.0.0.1:8001/docs'          # 问答 → 200
```

---

## 二、访问地址

| 用途 | 地址 | 账号 |
|------|------|------|
| 文件导入页面 | http://127.0.0.1:8000/import.html | — |
| 问题问答页面 | http://127.0.0.1:8001/chat.html | — |
| 导入接口文档 | http://127.0.0.1:8000/docs | — |
| 问答接口文档 | http://127.0.0.1:8001/docs | — |
| Milvus 管理界面（Attu） | http://localhost:7000 | — |
| Neo4j 浏览器 | http://localhost:7474 | neo4j / 123123123 |
| MinIO 控制台 | http://localhost:9001 | minioadmin / minioadmin |

---

## 三、使用流程

### 流程 1：导入文档 → 构建知识库

1. 打开 **导入页** `http://127.0.0.1:8000/import.html`
2. 点击/拖拽上传文件（支持 **PDF / MD**）
3. 观察任务进度（页面每 2 秒轮询 `/status/{task_id}`）：
   - 状态流转：`上传中...` → `处理中...` → `已完成`（绿色）
   - 点开「日志」可看到节点逐个执行：`node_entry` → `node_pdf_to_md` → `node_md_img` → `node_document_split` → `node_item_name_recognition` → `node_bge_embedding` → `node_import_milvus`
4. 验证入库结果：
   - **Milvus**：打开 Attu，查看 `kb_chunks` 集合是否新增该文档切片
   - **Neo4j**：查看实体/关系图
   - **MinIO**：检查 `knowledge-base-files` 桶中是否有文件

> ⚠️ 注意：PDF 解析依赖 **MinerU** 云服务（`.env` 中的 `MINERU_API_TOKEN`）。当前是占位符，**导入 PDF 会失败**；传 MD 文件不依赖 MinerU，可直接入库。

### 流程 2：问答（检索增强生成）

1. 打开 **问答页** `http://127.0.0.1:8001/chat.html`
2. 输入问题并发送（例如“万用表怎么测量电压？”）
3. 页面交互：
   - 发送后立即建立 SSE 长连接 `/stream/{session_id}`
   - 「阶段进度」折叠面板实时显示：意图识别/改写 → 多路召回（向量 + HyDE + 联网） → RRF 融合 → Rerank 重排 → LLM 生成
   - 答案流式逐字输出（打字机效果），完成后展示引用图片/链接
4. 会话历史自动存入 MongoDB（`kb002` 库的 `chat_message` 集合），刷新页面或追问时保留上下文；点「清空对话」会删除该会话历史

### 流程 3：日常使用菜单

| 你想做什么 | 去哪里 |
|-----------|--------|
| 导入新文档 | import.html 页面上传 |
| 提问现有知识库 | chat.html 页面提问 |
| 查看知识库向量数据 | Attu（http://localhost:7000） |
| 查看知识图谱 | Neo4j Browser（http://localhost:7474） |
| 查看上传的原始文件 | MinIO 控制台（http://localhost:9001） |
| 查看聊天历史 | MongoDB Compass 连 `mongodb://localhost:27017`，库 `kb002` |

---

## 四、修改配置（.env）

所有连接地址 / 密钥 / 模型路径都在项目根目录 **`.env`** 中：

| 配置项 | 当前值 | 修改场景 |
|--------|--------|----------|
| `OPENAI_BASE_URL` | `https://api.moonshot.cn/v1` | 换模型供应商时改 |
| `OPENAI_API_KEY` | `sk-...`（Moonshot） | 换/更新密钥时改 |
| `LLM_DEFAULT_MODEL` / `VL_MODEL` | `kimi-k3.1-pro` | 换模型名时改 |
| `MINERU_API_TOKEN` | `TOKEN_EMPTY_FOR_NOW`（占位） | **必须换真实 Token** 才能解析 PDF |
| `MCP_DASHSCOPE_BASE_URL` | 百炼 WebSearch | 联网搜索端点 |
| `BGE_M3_PATH` / `BGE_RERANKER_LARGE` | `D:\ai_models\...` | 本地模型位置变动时改 |
| `MILVUS_URL` / `NEO4J_URI` / `MONGO_URL` / `MINIO_ENDPOINT` | `localhost` 系列 | 默认无需改 |

---

## 五、关闭服务

```powershell
# 关闭两个 Python 服务（按端口找 PID）
netstat -ano | findstr ":8000 :8001"
taskkill /PID <PID> /F

# 停容器（数据保留在 volumes/）
cd D:\Desktop\PythonProject
docker compose down

# 关 MinIO
Stop-Process -Name minio -Force
```

> 提示：如果想彻底停止但保留容器下次自动启动，也可以直接退出 Docker Desktop。
