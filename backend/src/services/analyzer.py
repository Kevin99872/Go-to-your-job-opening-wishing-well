"""
職位分析服務 - 評估職位風險等級和理由
"""

import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class JobAnalyzer:
    """分析職位信息並判斷風險等級"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        self.salary_stats = {}  # 緩存薪資統計
    
    def analyze(self, job_title: str, salary: str, company: str = '',
                description: str = '', salary_stats: Dict = None) -> Dict:
        """
        分析職位風險。優先用 AI 模型回傳完整 JSON；
        AI 不可用時退回規則分析。
        """
        try:
            if not salary_stats:
                salary_stats = self.get_salary_stats(job_title)

            # 優先：AI 完整分析
            if self.model_manager.has_model_configured():
                ai_result = self._get_ai_full_analysis(
                    job_title, salary or '薪資未標示', company, description or '', salary_stats
                )
                if ai_result:
                    ai_result['salaryStats'] = salary_stats
                    ai_result['source'] = 'ai'
                    return ai_result

            # 退回：規則分析
            salary_range = self._parse_salary(salary or '')
            result = self._perform_analysis(
                job_title=job_title,
                salary_range=salary_range,
                company=company,
                description=description or '',
                salary_stats=salary_stats
            )
            result['source'] = 'rule'
            return result

        except Exception as e:
            logger.error(f'分析失敗: {str(e)}')
            return {
                'riskLevel': 'unknown',
                'reasons': ['分析錯誤'],
                'score': 50,
                'recommendation': '',
                'error': str(e)
            }
    
    def _parse_salary(self, salary_text: str) -> Dict:
        """解析薪資文本"""
        import re
        
        cleaned = re.sub(r'[^\d~\-]', '', salary_text)
        
        if '~' in cleaned:
            parts = cleaned.split('~')
        elif '-' in cleaned:
            parts = cleaned.split('-')
        else:
            return {'min': 0, 'max': 0, 'text': salary_text}
        
        try:
            min_sal = int(parts[0]) if parts[0] else 0
            max_sal = int(parts[1]) if len(parts) > 1 and parts[1] else min_sal
            
            if salary_text.find('K') != -1 or salary_text.find('k') != -1:
                min_sal *= 1000
                max_sal *= 1000
            
            return {
                'min': min_sal,
                'max': max_sal,
                'text': salary_text
            }
        except:
            return {'min': 0, 'max': 0, 'text': salary_text}
    
    def _perform_analysis(self, job_title: str, salary_range: Dict, 
                         company: str, description: str, 
                         salary_stats: Dict) -> Dict:
        """執行分析邏輯"""
        
        reasons = []
        score = 50  # 初始分數
        
        # 檢查薪資是否過低
        if salary_stats:
            median = salary_stats.get('median', 0)
            min_industry = salary_stats.get('min', 0)
            
            if salary_range['max'] and salary_range['max'] < median * 0.8:
                reasons.append('薪資低於業界中位數 20%')
                score -= 15
            
            if salary_range['min'] and salary_range['min'] < min_industry:
                reasons.append('薪資低於業界最低標準')
                score -= 20
        
        # 檢查職位描述
        if description:
            red_flags = ['急徵', '立即上班', '高壓', '責任制', '無休假']
            for flag in red_flags:
                if flag in description:
                    reasons.append(f'職位描述包含「{flag}」相關詞')
                    score -= 5
        
        # 判斷風險等級
        if score < 30:
            risk_level = 'high'
        elif score < 60:
            risk_level = 'medium'
        else:
            risk_level = 'low'
        
        return {
            'riskLevel': risk_level,
            'reasons': reasons if reasons else ['暫無特殊風險因素'],
            'score': max(0, min(100, score)),
            'recommendation': self._get_recommendation(risk_level, reasons),
            'salaryStats': salary_stats
        }
    
    def _get_ai_full_analysis(self, job_title: str, salary: str,
                              company: str, description: str,
                              salary_stats: Dict) -> Dict:
        """
        讓 AI 模型（Ollama）回傳完整 JSON 分析結果。
        成功時回傳 dict，失敗時回傳 None（退回規則分析）。
        """
        try:
            median = salary_stats.get('median', 0) if salary_stats else 0
            median_str = f'（業界中位數約 {median//1000}K）' if median else ''

            prompt = f"""你是台灣職場風險分析師。請根據以下資訊，評估這個職缺的風險。

職位：{job_title}
公司：{company or '未知'}
薪資：{salary}{median_str}
描述：{description[:600] or '無'}

評分標準（0=最差，100=最好）：
- 薪資是否合理（對照業界）
- 描述中有無責任制、高壓、無休假、面議等紅旗詞
- 職稱是否符合薪資水準

請只輸出以下格式的 JSON，不要有任何其他文字：
{{"riskLevel":"high|medium|low","score":0-100,"reasons":["原因1","原因2"],"recommendation":"一句建議"}}"""

            response = self.model_manager.generate_response(prompt)
            if not response:
                return None

            # 從回應中擷取 JSON（模型可能夾雜多餘文字）
            import re
            match = re.search(r'\{.*?\}', response, re.DOTALL)
            if not match:
                logger.warning(f'AI 回應無法解析：{response[:120]}')
                return None

            result = json.loads(match.group())

            # 驗證欄位
            if result.get('riskLevel') not in ('high', 'medium', 'low'):
                return None

            result.setdefault('score', 50)
            result.setdefault('reasons', [])
            result.setdefault('recommendation', '')
            logger.info(f'AI 分析完成：{job_title} → {result["riskLevel"]} ({result["score"]}分)')
            return result

        except Exception as e:
            logger.warning(f'AI 完整分析失敗: {str(e)}')
            return None

    def _get_ai_insights(self, job_title: str, salary: str,
                         description: str, analysis: Dict) -> str:
        """舊式 AI 見解（保留相容性，新流程不使用）"""
        return ''
    
    def get_salary_stats(self, job_title: str) -> Dict:
        """獲取職位薪資統計"""
        
        # TODO: 從數據庫或外部 API 獲取統計數據
        # 這是示例數據
        
        stats_map = {
            'C# 軟體工程師':        {'min': 35000, 'median': 55000, 'max': 85000,  'count': 245},
            '.NET 軟體工程師':       {'min': 35000, 'median': 55000, 'max': 85000,  'count': 180},
            'Java 軟體工程師':       {'min': 35000, 'median': 58000, 'max': 100000, 'count': 320},
            'Python 工程師':         {'min': 38000, 'median': 60000, 'max': 110000, 'count': 280},
            '前端工程師':            {'min': 35000, 'median': 55000, 'max': 95000,  'count': 410},
            '後端工程師':            {'min': 38000, 'median': 60000, 'max': 100000, 'count': 380},
            '全端工程師':            {'min': 40000, 'median': 65000, 'max': 110000, 'count': 200},
            'React 工程師':          {'min': 38000, 'median': 60000, 'max': 100000, 'count': 160},
            'Vue 工程師':            {'min': 35000, 'median': 55000, 'max': 90000,  'count': 150},
            'DevOps 工程師':         {'min': 45000, 'median': 70000, 'max': 120000, 'count': 130},
            '資料工程師':            {'min': 40000, 'median': 65000, 'max': 110000, 'count': 120},
            '資料分析師':            {'min': 35000, 'median': 50000, 'max': 80000,  'count': 200},
            'UI/UX 設計師':          {'min': 30000, 'median': 45000, 'max': 75000,  'count': 180},
            '產品經理':              {'min': 40000, 'median': 65000, 'max': 110000, 'count': 150},
            '專案經理':              {'min': 38000, 'median': 58000, 'max': 95000,  'count': 170},
            'QA 工程師':             {'min': 30000, 'median': 45000, 'max': 70000,  'count': 160},
            '系統工程師':            {'min': 35000, 'median': 52000, 'max': 80000,  'count': 190},
            '網路工程師':            {'min': 33000, 'median': 50000, 'max': 78000,  'count': 140},
            '資安工程師':            {'min': 40000, 'median': 65000, 'max': 110000, 'count': 100},
            'iOS 工程師':            {'min': 38000, 'median': 62000, 'max': 100000, 'count': 120},
            'Android 工程師':        {'min': 38000, 'median': 60000, 'max': 100000, 'count': 130},
        }

        # 模糊匹配：職稱包含關鍵字時回傳對應統計
        for key, stats in stats_map.items():
            if key in job_title or job_title in key:
                return stats

        return stats_map.get(job_title, {
            'min': 30000,
            'median': 50000,
            'max': 100000
        })
    
    def _get_recommendation(self, risk_level: str, reasons: List[str]) -> str:
        """根據風險等級和原因生成建議"""
        
        recommendations = {
            'high': '⚠️ 不建議投遞此職位，建議繼續尋找其他機會',
            'medium': '⚠️ 審慎考慮，可與現公司/其他職位比較後決定',
            'low': '✓ 此職位相對合理，值得進一步了解'
        }
        
        return recommendations.get(risk_level, '無法判斷')
