import os
import random
from datetime import datetime

import httpx
from langchain_core.tools import tool

from app.agent.tools.middleware import get_context
from app.core.config import settings
from app.rag.rag_service import RagSummarizeService
from app.rag.vector_store import VectorStoreService
from app.utils.logger_handler import logger
from app.utils.path_tools import get_abs_path

vector_store = VectorStoreService()
rag = RagSummarizeService(vector_store)

user_ids = ["1001", "1002", "1003", "1004", "1005", "1006", "1007", "1008", "1009", "1010"]
external_data: dict = {}

AMAP_KEY = settings.AMAP_API_KEY


def _amap_get(path: str, params: dict) -> dict:
    params["key"] = AMAP_KEY
    url = f"https://restapi.amap.com/v3{path}"
    try:
        resp = httpx.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"[Amap] API 调用失败: {e}")
        return {"status": "0", "info": str(e)}


def _city_to_adcode(city: str) -> str:
    data = _amap_get("/geocode/geo", {"address": city})
    geocodes = data.get("geocodes", [])
    if geocodes and geocodes[0].get("adcode"):
        return geocodes[0]["adcode"]
    return ""


@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="获取指定城市的实时天气信息，包括天气状况、气温、湿度、风向风力、降雨概率等")
def get_weather(city: str) -> str:
    adcode = _city_to_adcode(city)
    if not adcode:
        ip_data = _amap_get("/ip", {})
        adcode = ip_data.get("adcode", "")

    if not adcode:
        return f"未找到城市 {city} 的天气数据"

    data = _amap_get("/weather/weatherInfo", {"city": adcode, "extensions": "all"})
    if data.get("status") != "1":
        return f"获取{city}天气失败: {data.get('info', '未知错误')}"

    forecasts = data.get("forecasts", [])
    if not forecasts:
        return f"未找到{city}的天气预报"

    forecast = forecasts[0]
    today = forecast.get("casts", [{}])[0] if forecast.get("casts") else {}

    lines = [f"城市：{forecast.get('city', city)}"]
    if today:
        lines.extend([
            f"日期：{today.get('date', '未知')}",
            f"白天天气：{today.get('dayweather', '未知')}",
            f"夜间天气：{today.get('nightweather', '未知')}",
            f"气温：{today.get('nighttemp', '?')}°C ~ {today.get('daytemp', '?')}°C",
            f"风向：{today.get('daywind', '未知')} {today.get('daypower', '')}",
        ])

    return "\n".join(lines)


@tool(description="获取当前用户所在城市名称，基于 IP 定位")
def get_user_location() -> str:
    data = _amap_get("/ip", {})
    if data.get("status") == "1":
        city = data.get("city", "")
        if not city:
            city = data.get("province", "未知")
        logger.info(f"[IP定位] 城市: {city}")
        return city if city else "深圳"
    return "深圳"


@tool(description="获取用户ID，以纯字符形式返回")
def get_user_id() -> str:
    return random.choice(user_ids)


@tool(description="获取当前真实月份，格式 YYYY-MM")
def get_current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def generate_external_data():
    if external_data:
        return

    data_path = get_abs_path(settings.external_data_path)
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"外部数据文件不存在: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        for line in f.readlines()[1:]:
            arr = line.strip().split(",")
            user_id = arr[0].replace('"', "")
            feature = arr[1].replace('"', "")
            efficiency = arr[2].replace('"', "")
            consumables = arr[3].replace('"', "")
            comparison = arr[4].replace('"', "")
            time = arr[5].replace('"', "")

            if user_id not in external_data:
                external_data[user_id] = {}
            external_data[user_id][time] = {
                "特征": feature,
                "效率": efficiency,
                "耗材": consumables,
                "对比": comparison,
            }


@tool(description="检索指定用户在指定月份的扫地/扫拖机器人完整使用记录")
def fetch_external_data(user_id: str, month: str) -> str:
    generate_external_data()
    try:
        data = external_data[user_id][month]
        return (
            f"用户 {user_id} 在 {month} 的使用记录：\n"
            f"- 清扫特征：{data['特征']}\n"
            f"- 清扫效率：{data['效率']}\n"
            f"- 耗材状态：{data['耗材']}\n"
            f"- 与上月对比：{data['对比']}"
        )
    except KeyError:
        logger.warning(f"[fetch_external_data] 未检索到用户:{user_id} 在 {month} 的数据")
        return ""


@tool(description="无入参，调用后触发报告生成模式，为后续提示词切换提供上下文支撑")
def fill_context_for_report():
    get_context().report = True
    logger.info("[fill_context_for_report] 已设置 report=True")
    return "报告模式已激活，提示词已切换为报告生成模板"