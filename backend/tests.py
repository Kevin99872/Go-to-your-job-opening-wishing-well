"""
測試套件 - 單元測試和集成測試
"""

import unittest
import json
from unittest.mock import patch, MagicMock
import sys
import os

# 添加父級目錄到路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.analyzer import JobAnalyzer
from src.services.crawler import JobCrawler
from src.services.models import ModelManager


class TestJobAnalyzer(unittest.TestCase):
    """測試職位分析器"""
    
    def setUp(self):
        self.model_manager = MagicMock()
        self.analyzer = JobAnalyzer(self.model_manager)
    
    def test_parse_salary_range(self):
        """測試薪資解析"""
        result = self.analyzer._parse_salary("45K~60K")
        self.assertEqual(result['min'], 45000)
        self.assertEqual(result['max'], 60000)
    
    def test_parse_salary_monthly(self):
        """測試月薪解析"""
        result = self.analyzer._parse_salary("月薪 40,000~60,000")
        self.assertEqual(result['min'], 40000)
        self.assertEqual(result['max'], 60000)
    
    def test_analyze_low_salary(self):
        """測試低薪識別"""
        result = self.analyzer.analyze(
            job_title='C# 軟體工程師',
            salary='25K~35K',
            company='Test Company',
            description='急徵',
            salary_stats={'median': 55000, 'min': 35000}
        )
        
        self.assertEqual(result['riskLevel'], 'high')
        self.assertIn('薪資低於業界', ' '.join(result['reasons']))
    
    def test_get_salary_stats(self):
        """測試薪資統計獲取"""
        stats = self.analyzer.get_salary_stats('C# 軟體工程師')
        
        self.assertIn('min', stats)
        self.assertIn('median', stats)
        self.assertIn('max', stats)


class TestJobCrawler(unittest.TestCase):
    """測試職位爬蟲"""
    
    def setUp(self):
        self.crawler = JobCrawler()
    
    def test_parse_salary_with_k(self):
        """測試 K 單位薪資解析"""
        result = self.crawler._parse_salary("45K~60K")
        self.assertEqual(result['min'], 45000)
        self.assertEqual(result['max'], 60000)
    
    def test_parse_salary_with_comma(self):
        """測試逗號分隔薪資解析"""
        result = self.crawler._parse_salary("45,000~60,000")
        self.assertEqual(result['min'], 45000)
        self.assertEqual(result['max'], 60000)
    
    def test_parse_invalid_salary(self):
        """測試無效薪資處理"""
        result = self.crawler._parse_salary("面議")
        self.assertEqual(result['min'], 0)
        self.assertEqual(result['max'], 0)


class TestModelManager(unittest.TestCase):
    """測試模型管理器"""
    
    def test_has_model_configured_openai(self):
        """測試 OpenAI 配置檢查"""
        manager = ModelManager()
        manager.config = {
            'model_type': 'openai',
            'api_key': 'sk-test-key'
        }
        
        self.assertTrue(manager.has_model_configured())
    
    def test_has_model_configured_no_key(self):
        """測試無 API Key 時的檢查"""
        manager = ModelManager()
        manager.config = {
            'model_type': 'openai',
            'api_key': None
        }
        
        self.assertFalse(manager.has_model_configured())
    
    def test_has_model_configured_local(self):
        """測試本地模型配置檢查"""
        manager = ModelManager()
        manager.config = {
            'model_type': 'local',
            'local_url': 'http://localhost:11434'
        }
        
        self.assertTrue(manager.has_model_configured())


class TestIntegration(unittest.TestCase):
    """集成測試"""
    
    @patch('requests.get')
    def test_crawl_and_analyze_flow(self, mock_get):
        """測試爬蟲到分析的完整流程"""
        
        # 模擬 HTTP 請求
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<html>...</html>'
        mock_get.return_value = mock_response
        
        # 測試流程
        crawler = JobCrawler()
        model_manager = MagicMock()
        analyzer = JobAnalyzer(model_manager)
        
        # 驗證分析邏輯可以正常運行
        result = analyzer.analyze(
            job_title='C# 軟體工程師',
            salary='45K~60K',
            company='Test Corp',
            description=''
        )
        
        self.assertIn('riskLevel', result)
        self.assertIn('reasons', result)
        self.assertIn('score', result)


def run_tests():
    """運行所有測試"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加測試
    suite.addTests(loader.loadTestsFromTestCase(TestJobAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestJobCrawler))
    suite.addTests(loader.loadTestsFromTestCase(TestModelManager))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # 運行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
