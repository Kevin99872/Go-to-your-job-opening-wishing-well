"""
職位分析服務 - 評估職位風險等級和理由
"""

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
        分析職位風險
        
        Returns:
            {
                'riskLevel': 'high' | 'medium' | 'low',
                'reasons': ['原因1', '原因2', ...],
                'score': 0-100,
                'recommendation': '建議...'
            }
        """
        try:
            # 解析薪資信息
            salary_range = self._parse_salary(salary)
            
            # 獲取統計數據
            if not salary_stats:
                salary_stats = self.get_salary_stats(job_title)
            
            # 分析
            analysis = self._perform_analysis(
                job_title=job_title,
                salary_range=salary_range,
                company=company,
                description=description,
                salary_stats=salary_stats
            )
            
            # 使用 AI 模型進行深度分析
            if self.model_manager.has_model_configured():
                ai_insights = self._get_ai_insights(
                    job_title, salary, description, analysis
                )
                analysis['ai_insights'] = ai_insights
            
            return analysis
        
        except Exception as e:
            logger.error(f'分析失敗: {str(e)}')
            return {
                'riskLevel': 'unknown',
                'reasons': ['分析錯誤'],
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
            'recommendation': self._get_recommendation(risk_level, reasons)
        }
    
    def _get_ai_insights(self, job_title: str, salary: str, 
                        description: str, analysis: Dict) -> str:
        """使用 AI 模型獲取深度見解"""
        try:
            prompt = f"""
            請分析以下職位信息：
            職位：{job_title}
            薪資：{salary}
            風險等級：{analysis['riskLevel']}
            
            職位描述：{description[:500]}
            
            請簡要提出建議（100字以內）
            """
            
            response = self.model_manager.generate_response(prompt)
            return response
        
        except Exception as e:
            logger.warning(f'AI 分析失敗: {str(e)}')
            return ''
    
    def get_salary_stats(self, job_title: str) -> Dict:
        """獲取職位薪資統計"""
        
        # TODO: 從數據庫或外部 API 獲取統計數據
        # 這是示例數據
        
        stats_map = {
            'C# 軟體工程師': {
                'min': 35000,
                'median': 55000,
                'max': 80000,
                'count': 245
            },
            '.NET 軟體工程師': {
                'min': 35000,
                'median': 55000,
                'max': 85000,
                'count': 180
            }
        }
        
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
