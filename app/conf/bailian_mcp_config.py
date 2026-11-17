# 导入核心依赖：数据类、环境变量读取、路径处理
from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()


# 定义mcp的服务配置
@dataclass
class McpConfig:
    mcp_base_url: str
    api_key: str

    @property
    def auth_header(self) -> str:
        """
        生成用于 MCP SSE 请求的 Authorization 请求头。
        阿里云百炼 MCP 外部调用要求格式为: Authorization: Bearer <百炼API Key>
        这里做兼容处理：如果 Key 本身已带 "Bearer " 前缀则直接使用，否则自动补齐。
        """
        key = (self.api_key or "").strip()
        if not key:
            return ""
        if key.lower().startswith("bearer "):
            return key
        return f"Bearer {key}"


mcp_config = McpConfig(
    mcp_base_url=os.getenv("MCP_DASHSCOPE_BASE_URL"),
    # 优先使用百炼专用 Key（MCP_DASHSCOPE_API_KEY），
    # 未配置时回退到 OPENAI_API_KEY，保证旧配置不报错（但仍需换成百炼 Key 才能连上）。
    api_key=os.getenv("MCP_DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
)
