import os
import json
import urllib.request
import urllib.error
from .errors import ApiKeyMissingError, ApiCallError


class AiClient:
    def __init__(self, api_key: str, base_url: str, model: str, temperature: float, max_tokens: int):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls, model: str, temperature: float, max_tokens: int) -> 'AiClient':
        api_key = os.environ.get('AI_API_KEY')
        if not api_key:
            raise ApiKeyMissingError()
        
        base_url = os.environ.get('AI_API_BASE', 'https://copa.codyssey.kr/v1/chat/completions')
        return cls(api_key, base_url, model, temperature, max_tokens)

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }
        
        json_data = json.dumps(payload).encode('utf-8')
        
        request = urllib.request.Request(
            self.base_url,
            data=json_data,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            },
            method='POST'
        )
        
        try:
            with urllib.request.urlopen(request) as response:
                response_data = json.loads(response.read().decode('utf-8'))
                return response_data['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            raise ApiCallError('AI API 호출 실패', error_body)
        except urllib.error.URLError as e:
            raise ApiCallError('AI API 호출 실패', str(e.reason))
        except (json.JSONDecodeError, KeyError) as e:
            raise ApiCallError('AI API 응답 파싱 실패', str(e))
