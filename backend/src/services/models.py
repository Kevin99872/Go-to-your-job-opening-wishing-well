"""
模型管理服務 - 管理 AI 模型配置和調用
支援 OpenAI、Claude、本地模型 (Ollama)
"""

import os
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class ModelManager:
    """管理 AI 模型配置和調用"""
    
    def __init__(self):
        self.config = self._load_config()
        self.client = None
        self._initialize_client()
    
    def _load_config(self) -> Dict:
        """載入配置文件或環境變數"""
        config = {
            'model_type':   os.getenv('MODEL_TYPE', 'local'),
            'api_key':      os.getenv('API_KEY'),
            'local_url':    os.getenv('LOCAL_URL', 'http://localhost:11434'),
            'ollama_model': os.getenv('OLLAMA_MODEL', 'gemma4:latest')
        }
        
        # 如果有本地配置文件，優先使用
        try:
            import json
            if os.path.exists('config.json'):
                with open('config.json', 'r') as f:
                    local_config = json.load(f)
                    config.update(local_config)
        except:
            pass
        
        return config
    
    def _initialize_client(self):
        """初始化 AI 客戶端"""
        try:
            model_type = self.config.get('model_type', 'openai')
            
            if model_type == 'openai':
                try:
                    import openai
                    openai.api_key = self.config.get('sk-852cb3cc1f49455196aa1006fa3d64dc525331a8b5264670')
                    self.client = openai
                    logger.info('OpenAI 客戶端已初始化')
                except ImportError:
                    logger.warning('未安裝 openai 模塊')
            
            elif model_type == 'claude':
                try:
                    import anthropic
                    self.client = anthropic.Anthropic(
                        api_key=self.config.get('api_key')
                    )
                    logger.info('Claude 客戶端已初始化')
                except ImportError:
                    logger.warning('未安裝 anthropic 模塊')
            
            elif model_type == 'local':
                try:
                    import requests
                    # 簡單檢查本地模型是否可用
                    response = requests.get(
                        f"{self.config.get('local_url')}/api/tags",
                        timeout=3
                    )
                    if response.status_code == 200:
                        logger.info('本地模型已連接')
                    else:
                        logger.warning('本地模型連接失敗')
                except:
                    logger.warning('無法連接本地模型服務')
        
        except Exception as e:
            logger.error(f'初始化客戶端失敗: {str(e)}')
    
    def has_model_configured(self) -> bool:
        """檢查是否有模型配置"""
        model_type = self.config.get('model_type')
        
        if model_type in ['openai', 'claude']:
            return bool(self.config.get('api_key'))
        elif model_type == 'local':
            return True
        
        return False
    
    def generate_response(self, prompt: str) -> str:
        """
        使用配置的模型生成回應
        
        Args:
            prompt: 提示詞
        
        Returns:
            模型的回應
        """
        try:
            model_type = self.config.get('model_type')
            
            if model_type == 'openai':
                return self._openai_generate(prompt)
            elif model_type == 'claude':
                return self._claude_generate(prompt)
            elif model_type == 'local':
                return self._local_generate(prompt)
            else:
                return ''
        
        except Exception as e:
            logger.error(f'生成回應失敗: {str(e)}')
            return ''
    
    def _openai_generate(self, prompt: str) -> str:
        """使用 OpenAI 生成"""
        try:
            response = self.client.chat.completions.create(
                model='gpt-3.5-turbo',
                messages=[
                    {
                        'role': 'system',
                        'content': '你是一個職位評估專家，幫助台灣勞工識別不合理的工作條件。'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f'OpenAI 調用失敗: {str(e)}')
            return ''
    
    def _claude_generate(self, prompt: str) -> str:
        """使用 Claude 生成"""
        try:
            response = self.client.messages.create(
                model='claude-3-haiku-20240307',
                max_tokens=200,
                system='你是一個職位評估專家，幫助台灣勞工識別不合理的工作條件。',
                messages=[
                    {'role': 'user', 'content': prompt}
                ]
            )
            
            return response.content[0].text
        
        except Exception as e:
            logger.error(f'Claude 調用失敗: {str(e)}')
            return ''
    
    def _local_generate(self, prompt: str) -> str:
        """使用本地模型生成"""
        try:
            import requests
            
            response = requests.post(
                f"{self.config.get('local_url')}/api/generate",
                json={
                    'model': self.config.get('ollama_model', 'llama2'),
                    'prompt': prompt,
                    'stream': False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '')
            else:
                logger.warning(f'本地模型返回錯誤: {response.status_code}')
                return ''
        
        except Exception as e:
            logger.error(f'本地模型調用失敗: {str(e)}')
            return ''
    
    def set_config(self, config: Dict):
        """更新配置"""
        self.config.update(config)
        self._initialize_client()
        
        # 保存到文件
        try:
            import json
            with open('config.json', 'w') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            logger.info('配置已保存')
        except Exception as e:
            logger.error(f'保存配置失敗: {str(e)}')
    
    def get_config(self) -> Dict:
        """獲取配置"""
        return self.config.copy()
