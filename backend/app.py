"""
台灣求職避雷器 - Flask 後端服務
主要功能：
- 數據爬蟲（從 104 網站爬取職位信息）
- AI 模型集成（支援 OpenAI、Claude、本地模型）
- 職位分析和風險評估
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import json
from dotenv import load_dotenv
import logging

from src.services.crawler import JobCrawler
from src.services.analyzer import JobAnalyzer
from src.services.models import ModelManager

# 載入環境變數
load_dotenv()

# 初始化應用
app = Flask(__name__)
CORS(app)

# 配置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化服務
crawler = JobCrawler()
model_manager = ModelManager()
analyzer = JobAnalyzer(model_manager)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        'status': 'healthy',
        'service': '台灣求職避雷器'
    })


@app.route('/api/analyze', methods=['POST'])
def analyze_job():
    """分析職位信息"""
    try:
        data = request.json
        
        job_title = data.get('jobTitle')
        salary = data.get('salary')
        company = data.get('company')
        description = data.get('description')
        salary_stats = data.get('salaryStats')
        
        if not job_title or not salary:
            return jsonify({'error': '缺少必要信息'}), 400
        
        # 執行分析
        result = analyzer.analyze(
            job_title=job_title,
            salary=salary,
            company=company,
            description=description,
            salary_stats=salary_stats
        )
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f'分析職位失敗: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/salary-stats', methods=['GET'])
def get_salary_stats():
    """獲取職位薪資統計"""
    try:
        job_title = request.args.get('jobTitle')
        
        if not job_title:
            return jsonify({'error': '缺少職位名稱'}), 400
        
        # 從數據庫或爬蟲獲取統計
        stats = analyzer.get_salary_stats(job_title)
        
        return jsonify(stats)
    
    except Exception as e:
        logger.error(f'獲取薪資統計失敗: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/crawl', methods=['POST'])
def trigger_crawl():
    """觸發數據爬蟲"""
    try:
        # 爬取最新的職位信息
        result = crawler.crawl_104()
        
        return jsonify({
            'status': 'success',
            'jobs_count': result.get('count', 0),
            'message': '爬蟲完成'
        })
    
    except Exception as e:
        logger.error(f'爬蟲失敗: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """更新模型配置"""
    try:
        config = request.json
        
        # 驗證並保存配置
        model_manager.set_config(config)
        
        return jsonify({
            'status': 'success',
            'message': '配置已更新'
        })
    
    except Exception as e:
        logger.error(f'配置更新失敗: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """獲取當前配置"""
    try:
        config = model_manager.get_config()
        
        # 不返回敏感信息
        safe_config = {
            'model_type': config.get('model_type'),
            'has_api_key': bool(config.get('api_key')),
            'local_url': config.get('local_url')
        }
        
        return jsonify(safe_config)
    
    except Exception as e:
        logger.error(f'獲取配置失敗: {str(e)}')
        return jsonify({'error': str(e)}), 500


@app.route('/api/ollama/models', methods=['GET'])
def get_ollama_models():
    """取得 Ollama 可用模型清單（代理請求）"""
    try:
        import requests as req
        config = model_manager.get_config()
        ollama_url = config.get('local_url', 'http://localhost:11434').rstrip('/')
        
        res = req.get(f'{ollama_url}/api/tags', timeout=5)
        res.raise_for_status()
        return jsonify(res.json())
    
    except Exception as e:
        logger.error(f'取得 Ollama 模型失敗: {str(e)}')
        return jsonify({'error': str(e), 'models': []}), 503


@app.route('/api/ollama/generate', methods=['POST'])
def ollama_generate():
    """代理 Ollama 生成請求（解決擴充功能 CORS 限制）"""
    try:
        import requests as req
        config = model_manager.get_config()
        ollama_url = config.get('local_url', 'http://localhost:11434').rstrip('/')
        
        payload = request.json or {}
        res = req.post(
            f'{ollama_url}/api/generate',
            json=payload,
            timeout=60,
            stream=False
        )
        res.raise_for_status()
        return jsonify(res.json())
    
    except Exception as e:
        logger.error(f'Ollama 生成失敗: {str(e)}')
        return jsonify({'error': str(e)}), 503


if __name__ == '__main__':
    app.run(debug=True, port=5000)
