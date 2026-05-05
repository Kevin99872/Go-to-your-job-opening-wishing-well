"""
爬蟲服務 - 從 104 人力銀行爬取職位信息
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import logging
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)


class JobCrawler:
    """爬取 104 職位信息"""
    
    def __init__(self):
        self.base_url = 'https://www.104.com.tw/jobs/search/'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.jobs_data = []
    
    def crawl_104(self, keywords: str = 'C# .NET', max_pages: int = 5) -> Dict:
        """
        爬取 104 上的職位信息
        
        Args:
            keywords: 搜尋關鍵字
            max_pages: 最多爬取頁數
        
        Returns:
            爬蟲結果
        """
        try:
            logger.info(f'開始爬取 104 職位: {keywords}')
            
            for page in range(1, max_pages + 1):
                url = self._build_url(keywords, page)
                logger.info(f'爬取第 {page} 頁: {url}')
                
                try:
                    jobs = self._fetch_page(url)
                    self.jobs_data.extend(jobs)
                    time.sleep(2)  # 避免請求過於頻繁
                
                except Exception as e:
                    logger.warning(f'爬取第 {page} 頁失敗: {str(e)}')
                    continue
            
            # 保存數據
            self._save_data()
            
            return {
                'status': 'success',
                'count': len(self.jobs_data),
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f'爬蟲錯誤: {str(e)}')
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _build_url(self, keywords: str, page: int) -> str:
        """構建搜尋 URL"""
        params = {
            'keyword': keywords,
            'page': page,
            'pagesize': 10
        }
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f'{self.base_url}?{query_string}'
    
    def _fetch_page(self, url: str) -> List[Dict]:
        """
        獲取單個頁面的職位信息
        
        Note: 這是簡化的實現。實際的 104 網站結構可能需要調整選擇器
        """
        response = requests.get(url, headers=self.headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            raise Exception(f'HTTP {response.status_code}')
        
        soup = BeautifulSoup(response.content, 'html.parser')
        jobs = []
        
        # 根據實際 HTML 結構調整選擇器
        job_items = soup.find_all('article')
        
        for item in job_items:
            try:
                job = self._extract_job_info(item)
                if job:
                    jobs.append(job)
            except Exception as e:
                logger.warning(f'提取職位信息失敗: {str(e)}')
                continue
        
        return jobs
    
    def _extract_job_info(self, item) -> Dict:
        """從 HTML 元素中提取職位信息"""
        try:
            title = item.find('h1')
            company = item.find('a', class_='company-name')
            salary = item.find('span', class_='salary')
            
            if not all([title, company, salary]):
                return None
            
            # 解析薪資範圍
            salary_text = salary.text.strip()
            salary_range = self._parse_salary(salary_text)
            
            return {
                'title': title.text.strip(),
                'company': company.text.strip(),
                'salary_text': salary_text,
                'salary_min': salary_range['min'],
                'salary_max': salary_range['max'],
                'url': item.find('a')['href'] if item.find('a') else '',
                'description': item.find('p', class_='summary')?.text.strip() or '',
                'crawled_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.warning(f'提取信息失敗: {str(e)}')
            return None
    
    def _parse_salary(self, salary_text: str) -> Dict:
        """
        解析薪資文本
        預期格式: "40K~60K" 或 "月薪 40,000~60,000"
        """
        import re
        
        # 移除非數字字符，只保留數字和 ~ -
        cleaned = re.sub(r'[^\d~\-]', '', salary_text)
        
        # 分割範圍
        if '~' in cleaned:
            parts = cleaned.split('~')
        elif '-' in cleaned:
            parts = cleaned.split('-')
        else:
            return {'min': 0, 'max': 0}
        
        try:
            min_sal = int(parts[0]) if parts[0] else 0
            max_sal = int(parts[1]) if len(parts) > 1 and parts[1] else min_sal
            
            # 如果是以 K 為單位，轉換為實際金額
            if salary_text.find('K') != -1 or salary_text.find('k') != -1:
                min_sal *= 1000
                max_sal *= 1000
            
            return {'min': min_sal, 'max': max_sal}
        
        except:
            return {'min': 0, 'max': 0}
    
    def _save_data(self):
        """保存爬蟲數據到文件"""
        try:
            filename = f'data/jobs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            os.makedirs('data', exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.jobs_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f'數據已保存到 {filename}')
        
        except Exception as e:
            logger.error(f'保存數據失敗: {str(e)}')


import os
