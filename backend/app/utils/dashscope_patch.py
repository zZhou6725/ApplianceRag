"""DashScope SSL 兼容性补丁。

Python OpenSSL 无法处理 DashScope 服务器的 SSL 重协商（renegotiation），
导致 SSLEOFError。curl_cffi 使用 curl 的 TLS 实现可以正常连接。

此模块在 dashscope 加载前替换其内部使用的 requests 为 curl_cffi.requests。
"""
import curl_cffi.requests as curl_requests


def apply():
    # 替换 dashscope 各模块中的 requests 引用
    _targets = [
        "dashscope.api_entities.http_request",
        "dashscope.api_entities.encryption",
        "dashscope.client.base_api",
        "dashscope.common.session_manager",
        "dashscope.common.utils",
        "dashscope.finetune.reinforcement.common.utils",
        "dashscope.utils.oss_utils",
    ]

    for mod_name in _targets:
        try:
            mod = __import__(mod_name, fromlist=["requests"])
            mod.requests = curl_requests
        except ImportError:
            pass