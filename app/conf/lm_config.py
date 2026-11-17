# 导入核心依赖：数据类、环境变量读取、路径处理
from dataclasses import dataclass
import os
from dotenv import load_dotenv

# 提前加载.env配置文件（必须在读取环境变量前执行，确保os.getenv能获取到值）
# 若.env不在项目根目录，可指定路径：load_dotenv(dotenv_path=Path(__file__).parent / ".env")
# override=True：强制 .env 优先于系统/用户环境变量，避免 Windows 中遗留的
# OPENAI_API_KEY/OPENAI_BASE_URL（如其他工具配置的历史值）覆盖项目配置。
load_dotenv(override=True)


# 定义minerU服务配置
@dataclass
class LLMConfig:
    base_url: str
    api_key : str
    lv_model: str
    llm_model: str
    llm_temperature: float
    # VL（视觉）独立配置：Mercury 系列无多模态能力，VL 任务需走专用端点
    vl_base_url: str = ""
    vl_api_key: str = ""

lm_config = LLMConfig(
    base_url=os.getenv("OPENAI_BASE_URL"),
    api_key=os.getenv("OPENAI_API_KEY"),
    lv_model=os.getenv("VL_MODEL"),
    llm_model=os.getenv("LLM_DEFAULT_MODEL"),
    llm_temperature=float(os.getenv("LLM_DEFAULT_TEMPERATURE")),
    vl_base_url=os.getenv("VL_BASE_URL", ""),
    vl_api_key=os.getenv("VL_API_KEY", os.getenv("OPENAI_API_KEY", ""))
)
