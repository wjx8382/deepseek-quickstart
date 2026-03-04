from typing import Any
import httpx
from datetime import datetime, date
from mcp.server.fastmcp import FastMCP

# 1. 初始化 FastMCP 服务器
# 创建一个名为 "weather" 的服务器实例。这个名字有助于识别这套工具。
mcp = FastMCP("weather")

# --- 常量定义 ---
# 美国国家气象局 (NWS) API 的基础 URL
NWS_API_BASE = "https://api.weather.gov"
# 设置请求头中的 User-Agent，很多公共 API 要求提供此信息以识别客户端
USER_AGENT = "weather-app/1.0"


# --- 辅助函数 ---

async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    一个通用的异步函数，用于向 NWS API 发起请求并处理常见的错误。

    Args:
        url (str): 要请求的完整 URL。

    Returns:
        dict[str, Any] | None: 成功时返回解析后的 JSON 字典，失败时返回 None。
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"  # NWS API 推荐的 Accept 头
    }
    # 使用 httpx.AsyncClient 来执行异步 HTTP GET 请求
    async with httpx.AsyncClient() as client:
        try:
            # 发起请求，设置了30秒的超时
            response = await client.get(url, headers=headers, timeout=30.0)
            # 如果响应状态码是 4xx 或 5xx（表示客户端或服务器错误），则会引发一个异常
            response.raise_for_status()
            # 如果请求成功，返回 JSON 格式的响应体
            return response.json()
        except httpx.HTTPStatusError as e:
            # HTTP 状态码错误
            print(f"HTTP 错误 {e.response.status_code}: {e.request.url}")
            return None
        except httpx.RequestError as e:
            # 网络请求错误
            print(f"请求错误: {e}")
            return None
        except Exception as e:
            # 其他异常
            print(f"未知错误: {e}")
            return None

def format_alert(feature: dict) -> str:
    """将单个天气预警的 JSON 数据格式化为人类可读的字符串。"""
    props = feature["properties"]
    # 使用 .get() 方法安全地访问字典键，如果键不存在则返回默认值，避免程序出错
    return f"""
事件: {props.get('event', '未知')}
区域: {props.get('areaDesc', '未知')}
严重性: {props.get('severity', '未知')}
描述: {props.get('description', '无描述信息')}
指令: {props.get('instruction', '无具体指令')}
"""

# --- MCP 工具定义 ---

@mcp.tool()
async def get_alerts(state: str) -> str:
    """
    获取美国某个州当前生效的天气预警信息。
    这个函数被 @mcp.tool() 装饰器标记，意味着它可以被大模型作为工具来调用。

    参数:
        state: 两个字母的美国州代码 (例如: CA, NY)。
    """
    # 构造请求特定州天气预警的 URL
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    # 健壮性检查：如果请求失败或返回的数据格式不正确
    if not data or "features" not in data:
        return "无法获取预警信息或未找到相关数据。"

    # 如果 features 列表为空，说明该州当前没有生效的预警
    if not data["features"]:
        return "该州当前没有生效的天气预警。"

    # 使用列表推导和 format_alert 函数来格式化所有预警信息
    alerts = [format_alert(feature) for feature in data["features"]]
    # 将所有预警信息用分隔线连接成一个字符串并返回
    return "\n---\n".join(alerts)

@mcp.tool()
async def get_forecast(
    latitude: float,
    longitude: float,
    target_date: str | None = None,  # 新增：可选的目標日期，格式 'YYYY-MM-DD'
) -> str:
    """
    根据给定的经纬度获取天气预报。可以指定具体日期（未来日期）。

    参数:
        latitude: 地点的纬度
        longitude: 地点的经度
        target_date: 可选，目标日期（格式 'YYYY-MM-DD'），例如 '2026-03-05'。
                     如果不传，默认取未来几个预报周期。
                     只支持未来 7 天内的日期，历史日期无效。
    """
    # 第一步：根据经纬度获取点信息，包含预报 URL
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "无法获取该地点的预报数据。"

    # 第二步：提取实际的预报 URL
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "无法获取详细的预报信息。"

    # 提取预报周期数据
    periods = forecast_data["properties"]["periods"]
    if not periods:
        return "该地点暂无可用预报。"

    # 解析 target_date（如果有）
    target_dt = None
    if target_date:
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
        except ValueError:
            return f"日期格式错误，请使用 'YYYY-MM-DD' 格式，例如 '2026-03-05'。"

    forecasts = []

    for period in periods:
        # 每个 period 有 startTime，例如 "2026-03-04T06:00:00-05:00"
        start_time_str = period["startTime"]
        try:
            # 处理时区信息，将 Z 替换为 +00:00
            if start_time_str.endswith('Z'):
                start_time_str = start_time_str.replace('Z', '+00:00')
            period_start_dt = datetime.fromisoformat(start_time_str).date()
        except ValueError:
            # 如果日期解析失败，跳过这个周期
            continue

        # 如果指定了日期，只保留匹配该天的周期
        if target_dt:
            if period_start_dt != target_dt:
                continue
        else:
            # 没指定日期时，维持原逻辑：只取前 5 个（可调整）
            if len(forecasts) >= 5:
                break

        forecast = f"""
{period['name']} ({period_start_dt.strftime('%Y-%m-%d')}):
温度: {period['temperature']}°{period['temperatureUnit']}
风力: {period['windSpeed']} {period['windDirection']}
预报: {period['detailedForecast']}
"""
        forecasts.append(forecast.strip())

    if not forecasts:
        if target_dt:
            return f"找不到 {target_date} 的预报数据（可能日期超出未来 7 天范围，或该天无资料）。"
        else:
            return "暂无可用预报周期。"

    # 将结果连接起来
    return "\n---\n".join(forecasts)


# --- 服务器启动 ---

# 这是一个标准的 Python 入口点检查
# 确保只有当这个文件被直接运行时，以下代码才会被执行
if __name__ == "__main__":
    # 初始化并运行 MCP 服务器
    # transport='stdio' 表示服务器将通过标准输入/输出(stdin/stdout)与客户端（如大模型）进行通信。
    # 这是与本地模型或调试工具交互的常见方式。
    mcp.run(transport='stdio')
