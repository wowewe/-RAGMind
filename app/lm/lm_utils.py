# 环境配置与依赖导入
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import LangChainException
from typing import Optional

# 项目内部依赖
from app.conf.lm_config import lm_config
from app.core.logger import logger

# 全局缓存：键为(模型名, JSON输出模式)元组，值为ChatOpenAI实例
# 作用：避免重复初始化客户端，提升性能，统一实例管理
_llm_client_cache = {}
# VL（视觉）专用缓存：Mercury 无多模态能力，VL 任务走独立端点
_vl_client_cache = {}


def _get_credentials(model: str):
    """根据模型名决定使用主配置还是 VL 配置。"""
    is_vl = bool(lm_config.lv_model) and model.lower() == lm_config.lv_model.lower()
    if is_vl:
        if not lm_config.vl_base_url:
            raise ValueError("[VL客户端] 配置缺失：请在.env中配置VL_BASE_URL（视觉模型API地址）")
        if not lm_config.vl_api_key:
            raise ValueError("[VL客户端] 配置缺失：请在.env中配置VL_API_KEY（视觉模型API密钥）")
        return lm_config.vl_base_url, lm_config.vl_api_key, True
    else:
        if not lm_config.base_url:
            raise ValueError("[LLM客户端] 配置缺失：请在.env中配置OPENAI_BASE_URL（大模型API地址）")
        if not lm_config.api_key:
            raise ValueError("[LLM客户端] 配置缺失：请在.env中配置OPENAI_API_KEY（大模型API密钥）")
        return lm_config.base_url, lm_config.api_key, False


def get_llm_client(model: Optional[str] = None, json_mode: bool = False) -> ChatOpenAI:
    """
    获取带全局缓存的LangChain ChatOpenAI客户端实例
    适配OpenAI/千问/即梦AI等**OpenAI兼容API**，支持自定义模型和JSON标准化输出
    核心特性：缓存机制+配置统一加载+异常精准捕获+国产模型参数适配
              + VL（视觉）模型自动路由到独立端点

    :param model: 模型名称，优先级：传入参数 > 配置文件lm_config.llm_model > 内置默认qwen3-32b
    :param json_mode: 是否开启JSON输出模式，开启后返回标准json_object格式（适配结构化数据解析）
    :return: 初始化完成的ChatOpenAI实例（优先从全局缓存获取，未命中则新建并缓存）
    :raise ValueError: 缺失API密钥/基础地址等核心配置
    :raise Exception: 模型初始化失败（LangChain封装层异常）
    """
    # 1. 确定目标模型（优先级递减，保证模型名非空）
    target_model = model or lm_config.llm_model or "qwen3-32b"

    # 判断是否走 VL 端点
    base_url, api_key, is_vl = _get_credentials(target_model)

    # VL 和普通 LLM 使用不同的缓存字典
    cache_dict = _vl_client_cache if is_vl else _llm_client_cache
    cache_key = (target_model, json_mode)

    # 2. 缓存命中：直接返回已初始化的实例，避免重复创建
    if cache_key in cache_dict:
        label = "[VL客户端]" if is_vl else "[LLM客户端]"
        logger.debug(f"{label} 缓存命中，直接返回实例：模型={target_model}，JSON模式={json_mode}")
        return cache_dict[cache_key]

    logger.info(f"[{'VL' if is_vl else 'LLM'}客户端] 开始初始化新实例：模型={target_model}，JSON模式={json_mode}，base_url={base_url}")

    # 3. 配置参数组装：区分「国产模型私有参数」和「OpenAI通用参数」
    # extra_body：千问/即梦等国产模型专属私有参数（LangChain透传至API）
    _qwen_hosts = ["qwen", "aliyun", "dashscope"]
    extra_body = {"enable_thinking": False} if any(h in (base_url or "").lower() for h in _qwen_hosts) else {}
    # model_kwargs：OpenAI通用参数，所有兼容API均支持
    model_kwargs = {}
    if json_mode:
        # 开启JSON标准输出模式，强制模型返回可解析的json_object
        model_kwargs["response_format"] = {"type": "json_object"}
        logger.debug(f"[{'VL' if is_vl else 'LLM'}客户端] 已开启JSON输出模式，模型将返回标准JSON结构")

    # 4. 客户端初始化：捕获LangChain封装层异常，抛出更友好的提示
    try:
        llm_client = ChatOpenAI(
            model=target_model,  # 目标模型名
            temperature=lm_config.llm_temperature or 0.1,  # 低温度保证输出确定性（0~1）
            api_key=api_key,  # API密钥（可能来自 VL 或主配置）
            base_url=base_url,  # API基础地址
            extra_body=extra_body,  # 国产模型私有参数透传
            model_kwargs=model_kwargs,  # OpenAI通用参数
            max_tokens=4096,  # 限制单次最大token数，防止reasoning模式耗尽上下文后返回空content
        )
    except LangChainException as e:
        raise Exception(f"[{'VL' if is_vl else 'LLM'}客户端] 模型【{target_model}】初始化失败（LangChain层）：{str(e)}") from e

    # 5. 新实例存入缓存，供后续调用复用
    cache_dict[cache_key] = llm_client
    label = "[VL客户端]" if is_vl else "[LLM客户端]"
    logger.info(f"{label} 实例初始化成功并缓存：模型={target_model}，JSON模式={json_mode}")

    return llm_client
