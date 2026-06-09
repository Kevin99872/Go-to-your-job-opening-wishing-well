"""
爬蟲服務 - 使用 104 官方 JSON API 爬取職缺資料
"""

import os
import re
import time
import json
import logging
import requests
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 104 官方搜尋 API
_API_URL = "https://www.104.com.tw/jobs/search/list"
_DETAIL_URL = "https://www.104.com.tw/job/ajax/content/{job_id}"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.104.com.tw/jobs/search/",
    "Accept": "application/json, text/plain, */*",
}


class JobCrawler:
    """使用 104 官方 JSON API 爬取職缺"""

    def __init__(self):
        self.jobs_data: List[Dict] = []

    # ─── 公開介面 ────────────────────────────────────────────────────────────

    def crawl_104(
        self,
        keywords: str = "軟體工程師",
        max_pages: int = 5,
        fetch_detail: bool = False,
    ) -> Dict:
        """
        爬取 104 職缺列表。

        Args:
            keywords:     搜尋關鍵字
            max_pages:    最多爬幾頁（每頁 30 筆）
            fetch_detail: 是否進一步爬職缺詳細頁（較慢，可取得工時描述）

        Returns:
            {"status", "count", "timestamp"}
        """
        self.jobs_data = []
        logger.info(f"開始爬取 104：關鍵字={keywords}, 最多 {max_pages} 頁")

        for page in range(1, max_pages + 1):
            try:
                jobs = self._fetch_list_page(keywords, page)
                if not jobs:
                    logger.info(f"第 {page} 頁無資料，停止")
                    break

                if fetch_detail:
                    jobs = [self._enrich_with_detail(j) for j in jobs]

                self.jobs_data.extend(jobs)
                logger.info(f"  第 {page} 頁：取得 {len(jobs)} 筆")
                time.sleep(1.5)

            except Exception as e:
                logger.warning(f"第 {page} 頁失敗：{e}")

        self._save_data()
        return {
            "status": "success",
            "count": len(self.jobs_data),
            "timestamp": datetime.now().isoformat(),
        }

    def get_jobs(self) -> List[Dict]:
        """回傳本次爬取結果"""
        return self.jobs_data

    # ─── 私有：列表頁 ────────────────────────────────────────────────────────

    def _fetch_list_page(self, keywords: str, page: int) -> List[Dict]:
        params = {
            "keyword":  keywords,
            "order":    15,       # 依相關度排序
            "asc":      0,
            "page":     page,
            "mode":     "s",
            "jobsource": "2018indexpoc",
        }
        resp = requests.get(_API_URL, headers=_HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        jobs = []
        for item in data.get("data", {}).get("list", []):
            job = self._parse_list_item(item)
            if job:
                jobs.append(job)
        return jobs

    def _parse_list_item(self, item: dict) -> Optional[Dict]:
        """將 API 單筆 item 轉為統一格式"""
        try:
            job_id = item.get("jobNo", "")
            salary_text = item.get("salaryDesc", "")
            salary_range = _parse_salary(salary_text)

            # 工時：optimum/jobType
            work_type = item.get("jobType", "")        # 全職/兼職
            period    = item.get("periodDesc", "")     # 日班/夜班...

            # 加班關鍵字初步偵測
            tags = " ".join(item.get("tags", {}).get("tools", []))
            desc_snippet = item.get("description", "") or ""
            overtime_hint = _detect_overtime_keywords(desc_snippet + " " + tags)

            return {
                # 基本識別
                "jobId":       job_id,
                "jobUrl":      f"https://www.104.com.tw/job/{job_id}",
                "jobTitle":    item.get("jobName", ""),
                "company":     item.get("custName", ""),
                "companyId":   item.get("custNo", ""),
                # 薪資
                "salaryText":  salary_text,
                "salaryMin":   salary_range["min"],
                "salaryMax":   salary_range["max"],
                "salaryType":  salary_range["type"],   # monthly/yearly/hourly/unknown
                # 工作條件
                "workType":    work_type,
                "period":      period,
                "location":    item.get("jobAddrNoDesc", ""),
                # 描述片段 & 關鍵字
                "descSnippet": desc_snippet[:300],
                "overtimeHint": overtime_hint,         # 0~3 估算加班指數
                # 元資料
                "crawledAt":   datetime.now().isoformat(),
            }
        except Exception as e:
            logger.warning(f"parse_list_item 失敗：{e}")
            return None

    # ─── 私有：詳細頁（選用）────────────────────────────────────────────────

    def _enrich_with_detail(self, job: Dict) -> Dict:
        """爬詳細頁，補充工時/加班描述（會額外耗時）"""
        try:
            job_id = job.get("jobId", "")
            if not job_id:
                return job
            url = _DETAIL_URL.format(job_id=job_id)
            resp = requests.get(url, headers=_HEADERS, timeout=10)
            if resp.status_code != 200:
                return job
            detail = resp.json().get("data", {})

            # 完整職缺描述
            full_desc = detail.get("jobDetail", {}).get("jobDescription", "")
            job["fullDescription"] = full_desc[:1000]

            # 每日工時（部分職缺有填）
            work_period = detail.get("jobDetail", {}).get("workPeriod", "")
            job["workPeriodDesc"] = work_period

            # 重新偵測加班指數（用完整描述）
            job["overtimeHint"] = _detect_overtime_keywords(full_desc)

            time.sleep(0.8)
        except Exception as e:
            logger.debug(f"enrich_detail 失敗 ({job.get('jobId')})：{e}")
        return job

    # ─── 私有：儲存 ─────────────────────────────────────────────────────────

    def _save_data(self):
        try:
            out_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))),
                "data"
            )
            os.makedirs(out_dir, exist_ok=True)
            filename = os.path.join(
                out_dir,
                f"jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.jobs_data, f, ensure_ascii=False, indent=2)
            logger.info(f"職缺資料已儲存：{filename}（共 {len(self.jobs_data)} 筆）")
        except Exception as e:
            logger.error(f"儲存失敗：{e}")


# ─── 工具函式 ────────────────────────────────────────────────────────────────

def _parse_salary(text: str) -> Dict:
    """
    解析 104 薪資描述 → {min, max, type}
    範例: '月薪 40,000～60,000元' / '年薪 100萬' / '時薪 200元'
    """
    if not text:
        return {"min": 0, "max": 0, "type": "unknown"}

    sal_type = "unknown"
    if "月薪" in text or "月" in text:
        sal_type = "monthly"
    elif "年薪" in text or "年" in text:
        sal_type = "yearly"
    elif "時薪" in text:
        sal_type = "hourly"

    # 取所有數字段
    nums = re.findall(r"[\d,]+", text.replace(",", ""))
    nums = [int(n) for n in nums if n]

    if not nums:
        return {"min": 0, "max": 0, "type": sal_type}

    sal_min = nums[0]
    sal_max = nums[-1] if len(nums) > 1 else nums[0]

    # 「萬」單位
    if "萬" in text:
        sal_min *= 10000
        sal_max *= 10000

    # 年薪 → 月薪換算（供 LSTM 特徵統一使用）
    if sal_type == "yearly" and sal_max > 0:
        sal_min = sal_min // 12
        sal_max = sal_max // 12

    return {"min": sal_min, "max": sal_max, "type": sal_type}


_OVERTIME_KEYWORDS = {
    # 高加班風險
    "high":   ["責任制", "無休假", "加班費另計", "視工作量", "需配合加班",
                "彈性上下班", "假日加班", "輪班", "大夜班"],
    # 中等加班風險
    "medium": ["偶爾加班", "彈性工時", "專案期間", "專案加班"],
    # 低加班風險
    "low":    ["準時下班", "不需加班", "週休二日", "Work-Life Balance"],
}

def _detect_overtime_keywords(text: str) -> int:
    """
    從文字偵測加班風險程度
    Returns: 0=低, 1=中低, 2=中高, 3=高
    """
    if not text:
        return 1  # 預設中低
    score = 1
    for kw in _OVERTIME_KEYWORDS["high"]:
        if kw in text:
            score = max(score, 3)
    for kw in _OVERTIME_KEYWORDS["medium"]:
        if kw in text:
            score = max(score, 2)
    for kw in _OVERTIME_KEYWORDS["low"]:
        if kw in text:
            score = min(score, 0)
    return score
