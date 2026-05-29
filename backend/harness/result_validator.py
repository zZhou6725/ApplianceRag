from skills.base import SkillResult


class ResultValidator:
    MAX_RETRIES = 3

    @staticmethod
    def validate(result: SkillResult | dict) -> bool:
        if result is None:
            return False
        if isinstance(result, dict):
            if result.get("error"):
                return False
            output = result.get("output")
        else:
            if result.error:
                return False
            output = result.output

        if output is None:
            return False
        if isinstance(output, str) and not output.strip():
            return False
        return True

    @staticmethod
    def should_retry(error_count: int) -> bool:
        return error_count < ResultValidator.MAX_RETRIES

    @staticmethod
    def get_fallback_response() -> str:
        return "抱歉，我暂时无法处理您的请求。请尝试换个方式提问，或联系人工客服。"
