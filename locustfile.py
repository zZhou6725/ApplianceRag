"""
ApplianceRAG 性能压测脚本
启动：locust -f locustfile.py --host=http://127.0.0.1:8000

两组对比测试：
1. 关闭缓存 → 记录基准数据
2. 开启缓存 → 对比优化幅度
"""
import time
from locust import HttpUser, task, between, events


class ApplianceRAGUser(HttpUser):
    """模拟真实用户：登录 → 发送多条不同问题"""
    wait_time = between(1, 3)  # 用户思考间隔 1-3s

    def on_start(self):
        """每个虚拟用户启动时登录获取 token"""
        resp = self.client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        if resp.status_code == 200:
            data = resp.json()["data"]
            self.token = data["token"]
        else:
            self.token = None

    @task(3)
    def chat_quick_question(self):
        """简单问题——快速响应"""
        self._chat("你好，请问怎么联系客服？")

    @task(2)
    def chat_weather_question(self):
        """天气查询——触发工具调用链（定位+天气+RAG）"""
        self._chat("东莞今天天气怎么样？扫地机器人要注意什么？")

    @task(1)
    def chat_report_question(self):
        """报告生成——最重的请求"""
        self._chat("生成我2025-06的使用报告")

    def _chat(self, message: str):
        if not self.token:
            return
        start = time.perf_counter()
        with self.client.post(
            "/chat/stream",
            json={
                "conversation_id": None,
                "message": message,
                "file_context": None,
                "file_name": None,
            },
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            catch_response=True,
            stream=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"HTTP {resp.status_code}")
                return

            # 读取 SSE 流直到 done/error
            first_token = None
            for line in resp.iter_lines():
                if line and line.startswith(b"event: done"):
                    elapsed = (time.perf_counter() - start) * 1000
                    resp.success()
                    # 上报自定义指标
                    events.request.fire(
                        request_type="SSE",
                        name="chat_stream",
                        response_time=elapsed,
                        response_length=0,
                    )
                    return
                elif line and line.startswith(b"event: error"):
                    elapsed = (time.perf_counter() - start) * 1000
                    resp.failure(f"SSE error: {line.decode('utf-8', errors='replace')[:100]}")
                    return
                elif line and line.startswith(b"data:") and first_token is None:
                    first_token = (time.perf_counter() - start) * 1000
                    # 可选：上报首 token 耗时
                    events.request.fire(
                        request_type="SSE",
                        name="chat_first_token",
                        response_time=first_token,
                        response_length=0,
                    )

            # 没收到 done 事件
            elapsed = (time.perf_counter() - start) * 1000
            resp.failure("Stream ended without done event")