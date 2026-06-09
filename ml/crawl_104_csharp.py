"""
104 C# / .NET 工程師職缺爬蟲 + 資料集建立
=========================================
使用 Playwright 真實瀏覽器，攔截 104 API XHR 取得職缺 JSON。

執行方式（需用系統 Python，因 .venv 無 pip/playwright）：
    python ml/crawl_104_csharp.py                    # 預設爬 5 頁 .NET工程師
    python ml/crawl_104_csharp.py --pages 10         # 指定頁數
    python ml/crawl_104_csharp.py --keyword "C# 工程師"
    python ml/crawl_104_csharp.py --no-crawl         # 只用已有資料重建資料集

輸出：
    data/jobs_csharp_<timestamp>.json       原始爬蟲資料
    cash dataset/employee_csharp.json       LSTM 訓練格式資料集
"""

import argparse
import json
import os
import re
import glob
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
CASH_DIR  = os.path.join(BASE_DIR, "cash dataset")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CASH_DIR, exist_ok=True)

KEYWORDS_DEFAULT = ".NET工程師"

# ─── 業界薪資基準（C#/.NET 工程師，月薪萬元）─────────────────────────────────
_BENCH = {"p25": 4.5, "p50": 5.8, "p75": 8.5}

_RED   = ["責任制","無休假","需配合加班","假日加班","輪班","大夜班",
          "急徵","立即上班","高壓","面議","依能力議定"]
_GREEN = ["準時下班","不需加班","週休二日","彈性上班",
          "股票","員工股","績效獎金","年終獎金","遠端","居家辦公"]
_OT_HIGH   = ["責任制","無休假","需配合加班","假日加班","輪班","大夜班"]
_OT_MEDIUM = ["偶爾加班","彈性工時","專案加班"]
_OT_LOW    = ["準時下班","不需加班","週休二日"]


# ══════════════════════════════════════════════════════════════════════════════
#  1. Playwright 爬蟲（攔截 API XHR）
# ══════════════════════════════════════════════════════════════════════════════

def crawl_with_playwright(keyword: str, max_pages: int = 5) -> List[Dict]:
    """使用 Playwright 攔截 104 API XHR，取得結構化職缺資料。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[錯誤] 未安裝 playwright，請執行：python -m pip install playwright && python -m playwright install chromium")
        return []

    all_jobs: List[Dict] = []
    api_pattern = re.compile(r"jobs/search/list", re.IGNORECASE)

    print(f"\n[Playwright] 關鍵字：{keyword}，目標 {max_pages} 頁")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="zh-TW",
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        # ── 先嘗試 XHR 攔截 ──────────────────────────────────────────────────
        captured_xhr: List[dict] = []

        def on_response(response):
            try:
                if api_pattern.search(response.url) and response.status == 200:
                    data = response.json()
                    jobs_list = data.get("data", {}).get("list", [])
                    if jobs_list:
                        captured_xhr.append(jobs_list)
                        print(f"  [XHR攔截] {len(jobs_list)} 筆")
            except Exception:
                pass

        page.on("response", on_response)

        kw_enc = quote(keyword)
        seen_ids: set = set()

        for pg in range(1, max_pages + 1):
            url = (f"https://www.104.com.tw/jobs/search/"
                   f"?keyword={kw_enc}&order=15&asc=0&page={pg}&mode=s")
            print(f"  [瀏覽] 第 {pg} 頁：{url}")
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)
            except Exception as e:
                print(f"  [warn] 第 {pg} 頁逾時：{e}")

            # ── 優先用 XHR 攔截資料 ──────────────────────────────────────
            if captured_xhr:
                for items in captured_xhr:
                    for item in items:
                        job_id = item.get("jobNo","")
                        if job_id and job_id not in seen_ids:
                            seen_ids.add(job_id)
                            job = _parse_item(item)
                            if job: all_jobs.append(job)
                captured_xhr.clear()
                print(f"  [XHR] 累計 {len(all_jobs)} 筆")
            else:
                # ── fallback：直接 DOM 解析 ───────────────────────────────
                dom_jobs = _parse_dom(page, seen_ids)
                all_jobs.extend(dom_jobs)
                print(f"  [DOM] 本頁 {len(dom_jobs)} 筆，累計 {len(all_jobs)} 筆")

            time.sleep(1.5)

        browser.close()

    print(f"\n[完成] 共取得 {len(all_jobs)} 筆職缺")
    return all_jobs


# ══════════════════════════════════════════════════════════════════════════════
#  2. 職缺資料解析
# ══════════════════════════════════════════════════════════════════════════════

def _parse_dom(page, seen_ids: set) -> List[Dict]:
    """從 Playwright 頁面 DOM 直接解析職缺卡片（XHR 攔截失敗時的 fallback）。"""
    jobs = []
    try:
        # 取得所有職缺連結
        links = page.query_selector_all("a[href*='/job/']")
        for link in links:
            href = link.get_attribute("href") or ""
            m    = re.search(r"/job/([a-zA-Z0-9]+)", href)
            if not m: continue
            job_id = m.group(1)
            if job_id in seen_ids: continue

            title = (link.inner_text() or "").strip()
            if not title or len(title) < 2 or len(title) > 60: continue

            # 向上找卡片容器
            card = link.evaluate("""el => {
                let p = el;
                for (let i=0; i<6; i++) {
                    p = p.parentElement;
                    if (!p) break;
                    const t = p.tagName.toLowerCase();
                    const c = p.className || '';
                    if (t==='li' || t==='article' || c.includes('b-block') || c.includes('job-list')) return p.outerHTML;
                }
                return el.parentElement?.parentElement?.outerHTML || '';
            }""")

            # 從卡片 HTML 中抓薪資、公司
            sal_text = ""
            company  = ""
            desc     = ""
            if card:
                sal_m = re.search(r'(?:月薪|年薪|時薪|待遇)[^\d<]*[\d,]+[^\d<]*(?:[\d,]+)?', card)
                if sal_m: sal_text = sal_m.group(0)[:50]
                # 簡單取純文字（去掉 HTML tag）
                text = re.sub(r"<[^>]+>", " ", card)
                text = re.sub(r"\s+", " ", text).strip()
                desc = text[:400]

            sal = _parse_salary(sal_text)
            ot  = _overtime_hint(desc)
            seen_ids.add(job_id)
            jobs.append({
                "jobId":       job_id,
                "jobUrl":      f"https://www.104.com.tw/job/{job_id}",
                "jobTitle":    title,
                "company":     company,
                "salaryText":  sal_text,
                "salaryMin":   sal["min"],
                "salaryMax":   sal["max"],
                "salaryType":  sal["type"],
                "location":    "",
                "descSnippet": desc,
                "tags":        "",
                "overtimeHint":ot,
                "crawledAt":   datetime.now().isoformat(),
            })
    except Exception as e:
        print(f"  [warn] _parse_dom 失敗：{e}")
    return jobs


def _parse_item(item: dict) -> Optional[Dict]:
    try:
        job_id   = item.get("jobNo", "")
        sal_text = item.get("salaryDesc", "")
        sal      = _parse_salary(sal_text)
        desc     = item.get("description", "") or ""
        tags     = " ".join(item.get("tags", {}).get("tools", []))
        ot_hint  = _overtime_hint(desc + " " + tags)

        return {
            "jobId":       job_id,
            "jobUrl":      f"https://www.104.com.tw/job/{job_id}",
            "jobTitle":    item.get("jobName", ""),
            "company":     item.get("custName", ""),
            "salaryText":  sal_text,
            "salaryMin":   sal["min"],
            "salaryMax":   sal["max"],
            "salaryType":  sal["type"],
            "location":    item.get("jobAddrNoDesc", ""),
            "descSnippet": desc[:400],
            "tags":        tags,
            "overtimeHint":ot_hint,
            "crawledAt":   datetime.now().isoformat(),
        }
    except Exception as e:
        print(f"  [warn] parse_item 失敗：{e}")
        return None


def _parse_salary(text: str) -> Dict:
    if not text:
        return {"min": 0, "max": 0, "type": "unknown"}
    sal_type = "monthly"
    if "年薪" in text:   sal_type = "yearly"
    elif "時薪" in text: sal_type = "hourly"
    nums = [int(n.replace(",", "")) for n in re.findall(r"[\d,]+", text)
            if n.replace(",", "").isdigit()]
    if not nums:
        return {"min": 0, "max": 0, "type": sal_type}
    lo, hi = min(nums), max(nums)
    if "萬" in text:
        lo *= 10000; hi *= 10000
    if sal_type == "yearly" and hi > 0:
        lo //= 12; hi //= 12
    return {"min": lo, "max": hi, "type": sal_type}


def _overtime_hint(text: str) -> int:
    if any(w in text for w in _OT_HIGH):   return 3
    if any(w in text for w in _OT_MEDIUM): return 2
    if any(w in text for w in _OT_LOW):    return 0
    return 1


# ══════════════════════════════════════════════════════════════════════════════
#  3. 轉換為 LSTM 訓練格式
# ══════════════════════════════════════════════════════════════════════════════

def to_employee_record(job: Dict) -> Optional[Dict]:
    try:
        lo = float(job.get("salaryMin", 0) or 0)
        hi = float(job.get("salaryMax", 0) or 0)
        if lo > 1000: lo /= 10000
        if hi > 1000: hi /= 10000
        monthly = (lo + hi) / 2
        if monthly <= 0:
            return None

        ot_hint   = int(job.get("overtimeHint", 1))
        desc      = job.get("descSnippet", "") or ""
        red_cnt   = sum(1 for w in _RED   if w in desc)
        green_cnt = sum(1 for w in _GREEN if w in desc)
        if red_cnt >= 2:
            ot_hint = min(ot_hint + 1, 3)

        daily, ot_mo, ot_freq = {0:(8.0,2,1),1:(8.5,8,2),2:(9.5,20,4),3:(11.0,40,5)}.get(ot_hint,(8.5,8,2))
        job_sat = max(1, min(5, _salary_score(monthly) + green_cnt - red_cnt))
        loading = {0:1,1:2,2:4,3:5}.get(ot_hint, 2)

        return {
            "timestamp":                job.get("crawledAt", datetime.now().isoformat()),
            "companyName":              job.get("company", ""),
            "position":                 job.get("jobTitle", ""),
            "jobLevel":                 "",
            "relevantExperience":       0,
            "currentTenure":            0,
            "monthlyBaseSalary":        round(monthly, 2),
            "monthlyBonus":             0,
            "totalAnnualCompensation":  str(round(monthly * 12, 1)),
            "dailyAverageWorkingHours": daily,
            "monthlyOvertime":          ot_mo,
            "overtimeFrequency":        ot_freq,
            "jobSatisfaction":          job_sat,
            "loading":                  loading,
            "supplement":               f"104爬蟲 red={red_cnt} green={green_cnt}",
            "_source":                  job.get("jobUrl", ""),
        }
    except Exception as e:
        print(f"  [warn] to_employee_record 失敗：{e}")
        return None


def _salary_score(m: float) -> int:
    if m >= _BENCH["p75"]: return 5
    if m >= _BENCH["p50"]: return 4
    if m >= _BENCH["p25"]: return 3
    if m >= _BENCH["p25"] * 0.8: return 2
    return 1


# ══════════════════════════════════════════════════════════════════════════════
#  4. 標籤統計
# ══════════════════════════════════════════════════════════════════════════════

def print_label_stats(records: List[Dict]):
    scores = []
    for r in records:
        sat  = int(r.get("jobSatisfaction", 3))
        load = int(r.get("loading", 3))
        ot   = float(r.get("monthlyOvertime", 0))
        hrs  = float(r.get("dailyAverageWorkingHours", 8))
        scores.append((5-sat) + (load-1) + (1 if ot>20 else 0) + (1 if hrs>9 else 0))
    arr    = np.array(scores)
    labels = np.where(arr<=3, 0, np.where(arr<=6, 1, 2))
    names  = {0:"好缺", 1:"普通", 2:"屎缺"}
    print("\n[標籤分佈]")
    for cls, name in names.items():
        cnt = (labels == cls).sum()
        print(f"  Class {cls} ({name}): {cnt} 筆 ({cnt/len(labels)*100:.1f}%)")


# ══════════════════════════════════════════════════════════════════════════════
#  5. 主流程
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="104 C#/.NET 工程師爬蟲 + 資料集建立")
    parser.add_argument("--pages",    type=int, default=5,          help="爬幾頁（預設 5）")
    parser.add_argument("--keyword",  default=KEYWORDS_DEFAULT,     help="搜尋關鍵字")
    parser.add_argument("--no-crawl", action="store_true",          help="跳過爬蟲，用已有資料")
    args = parser.parse_args()

    # ── 爬蟲 ──────────────────────────────────────────────────────────────────
    if args.no_crawl:
        files = sorted(glob.glob(os.path.join(DATA_DIR, "jobs_csharp_*.json")), reverse=True)
        if not files:
            print("[錯誤] 找不到已有資料，請移除 --no-crawl")
            return
        raw_path = files[0]
        print(f"[略過爬蟲] 使用：{raw_path}")
        with open(raw_path, encoding="utf-8") as f:
            jobs = json.load(f)
    else:
        jobs = crawl_with_playwright(keyword=args.keyword, max_pages=args.pages)
        if not jobs:
            print("[錯誤] 爬蟲無結果")
            return
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_path = os.path.join(DATA_DIR, f"jobs_csharp_{ts}.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(jobs, f, ensure_ascii=False, indent=2)
        print(f"\n[原始資料] 已儲存：{raw_path}（{len(jobs)} 筆）")

    # ── 轉換資料集 ────────────────────────────────────────────────────────────
    print(f"\n[轉換] {len(jobs)} 筆職缺 → LSTM 格式…")
    records = [to_employee_record(j) for j in jobs]
    records = [r for r in records if r]
    print(f"  成功：{len(records)} 筆，跳過（無薪資）：{len(jobs)-len(records)} 筆")

    out_path = os.path.join(CASH_DIR, "employee_csharp.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"[資料集] 已儲存：{out_path}（{len(records)} 筆）")

    print_label_stats(records)

    print("\n" + "="*55)
    print("後續步驟：")
    print(f'  重新訓練（含 C# 資料）：')
    print(f'  .venv\\Scripts\\python ml/train_lstm.py --data "cash dataset/employee_csharp.json"')
    print("="*55)


if __name__ == "__main__":
    main()
