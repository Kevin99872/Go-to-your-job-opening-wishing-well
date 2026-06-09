"""
Dataset Builder
將 104 爬蟲職缺 JSON → LSTM 訓練用 employee-format JSON

執行方式:
    python ml/dataset_builder.py                         # 使用 data/ 下最新爬蟲檔
    python ml/dataset_builder.py --input data/jobs_xxx.json
    python ml/dataset_builder.py --merge                 # 合併 employee.json + 爬蟲資料

輸出: cash dataset/employee_crawled.json
      （格式與 employee.json 相同，可直接傳給 train_lstm.py）
"""

import argparse
import json
import os
import re
import glob
from datetime import datetime
from typing import Dict, List, Optional

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
CASH_DIR  = os.path.join(BASE_DIR, "cash dataset")
OUT_PATH  = os.path.join(CASH_DIR, "employee_crawled.json")
ORIG_PATH = os.path.join(CASH_DIR, "employee.json")

# ─── 業界薪資參考（月薪，單位：萬元）────────────────────────────────────────
# 用於計算「薪資相對市場」特徵，並輔助自動標籤
_SALARY_BENCHMARKS = {
    "軟體工程師":   {"p25": 4.5, "p50": 5.8, "p75": 8.0},
    "前端工程師":   {"p25": 4.0, "p50": 5.5, "p75": 7.5},
    "後端工程師":   {"p25": 4.5, "p50": 6.0, "p75": 9.0},
    "全端工程師":   {"p25": 4.5, "p50": 6.5, "p75": 10.0},
    "資料工程師":   {"p25": 5.0, "p50": 6.5, "p75": 10.0},
    "資料分析師":   {"p25": 3.5, "p50": 5.0, "p75": 7.5},
    "DevOps":       {"p25": 5.0, "p50": 7.0, "p75": 11.0},
    "資安工程師":   {"p25": 5.0, "p50": 6.5, "p75": 10.0},
    "產品經理":     {"p25": 4.5, "p50": 6.5, "p75": 10.0},
    "QA 工程師":    {"p25": 3.5, "p50": 4.5, "p75": 6.5},
    "UI/UX":        {"p25": 3.0, "p50": 4.5, "p75": 7.0},
    "DEFAULT":      {"p25": 3.5, "p50": 5.0, "p75": 8.0},
}

# 紅旗詞 → 加分到「屎缺」分數
_RED_FLAG_WORDS = [
    "責任制", "無休假", "需配合加班", "假日加班", "輪班", "大夜班",
    "急徵", "立即上班", "高壓", "面議", "依能力議定",
]

# 綠旗詞 → 加分到「好缺」分數
_GREEN_FLAG_WORDS = [
    "準時下班", "不需加班", "週休二日", "彈性上班",
    "股票", "員工股", "績效獎金", "年終獎金",
]


# ─── 核心轉換 ─────────────────────────────────────────────────────────────────

def job_to_employee_record(job: Dict) -> Optional[Dict]:
    """
    將單筆 104 職缺 → employee.json 格式

    欄位對應策略：
        monthlyBaseSalary       → (salaryMin + salaryMax) / 2  (萬元)
        totalAnnualCompensation → monthlyBaseSalary * 12
        monthlyBonus            → 0（資訊不足，保守估計）
        dailyAverageWorkingHours→ 依 overtimeHint 估算
        monthlyOvertime         → 依 overtimeHint 估算
        overtimeFrequency       → 依 overtimeHint 對應
        relevantExperience      → 0（職缺資料無此欄，用預設）
        currentTenure           → 0
        jobSatisfaction         → 依自動標籤反推
        loading                 → 依 overtimeHint 反推
    """
    try:
        # ── 薪資（轉換為萬元）────────────────────────────────────────────
        sal_min = job.get("salaryMin", 0) or 0
        sal_max = job.get("salaryMax", 0) or 0
        if sal_min == 0 and sal_max == 0:
            return None   # 無薪資資訊，跳過

        # 原始單位判斷（104 API 回傳元）
        # 若值 > 1000 表示已是元，轉換為萬元
        if sal_min > 1000:
            sal_min = sal_min / 10000
        if sal_max > 1000:
            sal_max = sal_max / 10000

        monthly_salary = (sal_min + sal_max) / 2
        if monthly_salary <= 0:
            return None

        annual_comp = monthly_salary * 12

        # ── 加班指數 (0~3) → 工時 / 加班時數 / 頻率 ─────────────────────
        ot_hint = int(job.get("overtimeHint", 1))
        daily_hours, monthly_ot, ot_freq = _overtime_hint_to_features(ot_hint)

        # ── 合併描述文字偵測 ──────────────────────────────────────────────
        desc = (job.get("fullDescription") or job.get("descSnippet") or "")
        red_count   = sum(1 for w in _RED_FLAG_WORDS  if w in desc)
        green_count = sum(1 for w in _GREEN_FLAG_WORDS if w in desc)

        # 紅旗詞可能使加班特徵升高
        if red_count >= 2:
            ot_hint      = min(ot_hint + 1, 3)
            daily_hours  = max(daily_hours, 9.5)
            monthly_ot   = max(monthly_ot, 25)
            ot_freq      = max(ot_freq, 4)

        # ── 自動標籤（jobSatisfaction & loading） ────────────────────────
        job_sat, loading = _auto_label(
            monthly_salary=monthly_salary,
            job_title=job.get("jobTitle", ""),
            ot_hint=ot_hint,
            red_count=red_count,
            green_count=green_count,
        )

        return {
            "timestamp":               job.get("crawledAt", datetime.now().isoformat()),
            "companyName":             job.get("company", ""),
            "position":                job.get("jobTitle", ""),
            "jobLevel":                "",
            "relevantExperience":      0,
            "currentTenure":           0,
            "monthlyBaseSalary":       round(monthly_salary, 2),
            "monthlyBonus":            0,
            "totalAnnualCompensation": str(round(annual_comp, 1)),
            "dailyAverageWorkingHours":daily_hours,
            "monthlyOvertime":         monthly_ot,
            "overtimeFrequency":       ot_freq,
            "jobSatisfaction":         job_sat,
            "loading":                 loading,
            "supplement":              f"源自104爬蟲 redFlags={red_count} greenFlags={green_count}",
            # 保留原始 URL 供追溯
            "_source":                 job.get("jobUrl", ""),
        }

    except Exception as e:
        print(f"  [warn] job_to_employee_record 失敗：{e}")
        return None


# ─── 標籤推算 ─────────────────────────────────────────────────────────────────

def _overtime_hint_to_features(hint: int):
    """
    hint 0=低, 1=中低, 2=中高, 3=高
    Returns: (daily_hours, monthly_overtime, overtime_frequency)
    """
    table = {
        0: (8.0,  2,  1),
        1: (8.5,  8,  2),
        2: (9.5, 20,  4),
        3: (11.0, 40, 5),
    }
    return table.get(hint, (8.5, 8, 2))


def _get_salary_benchmark(job_title: str) -> Dict:
    for key, bench in _SALARY_BENCHMARKS.items():
        if key in job_title:
            return bench
    return _SALARY_BENCHMARKS["DEFAULT"]


def _auto_label(
    monthly_salary: float,
    job_title: str,
    ot_hint: int,
    red_count: int,
    green_count: int,
) -> tuple:
    """
    自動推算 jobSatisfaction (1~5) 與 loading (1~5)

    邏輯：
    - 薪資 >= p75 → 高滿意
    - 薪資 <= p25 → 低滿意
    - 加班 hint 高 → loading 高
    - 紅旗詞多 → 滿意度下降
    - 綠旗詞多 → 滿意度上升
    """
    bench = _get_salary_benchmark(job_title)
    p25, p50, p75 = bench["p25"], bench["p50"], bench["p75"]

    # 薪資分數 1~5
    if monthly_salary >= p75:
        sal_score = 5
    elif monthly_salary >= p50:
        sal_score = 4
    elif monthly_salary >= p25:
        sal_score = 3
    elif monthly_salary >= p25 * 0.8:
        sal_score = 2
    else:
        sal_score = 1

    # 調整
    sal_score = max(1, min(5, sal_score + green_count - red_count))

    # loading 1~5（加班指數直接映射）
    loading_map = {0: 1, 1: 2, 2: 4, 3: 5}
    loading = loading_map.get(ot_hint, 2)

    return sal_score, loading


# ─── 資料集合併 ───────────────────────────────────────────────────────────────

def build_dataset(input_path: str, merge_original: bool = False) -> List[Dict]:
    print(f"\n[1] 讀取爬蟲資料：{input_path}")
    with open(input_path, encoding="utf-8") as f:
        jobs = json.load(f)
    print(f"    共 {len(jobs)} 筆職缺")

    records = []
    skipped = 0
    for job in jobs:
        rec = job_to_employee_record(job)
        if rec:
            records.append(rec)
        else:
            skipped += 1
    print(f"    轉換成功：{len(records)} 筆，跳過（無薪資）：{skipped} 筆")

    if merge_original and os.path.exists(ORIG_PATH):
        print(f"\n[2] 合併原始 employee.json：{ORIG_PATH}")
        with open(ORIG_PATH, encoding="utf-8") as f:
            orig = json.load(f)
        records = orig + records
        print(f"    合併後共 {len(records)} 筆")

    return records


def find_latest_crawl_file() -> Optional[str]:
    files = sorted(glob.glob(os.path.join(DATA_DIR, "jobs_*.json")), reverse=True)
    return files[0] if files else None


# ─── Label 統計 ───────────────────────────────────────────────────────────────

def print_label_stats(records: List[Dict]):
    """印出標籤分佈（同 train_lstm.py 的標籤計算邏輯）"""
    import numpy as np
    print("\n[統計] 自動標籤分佈預覽：")
    scores = []
    for r in records:
        sat  = int(r.get("jobSatisfaction", 3))
        load = int(r.get("loading", 3))
        ot   = float(r.get("monthlyOvertime", 0))
        hrs  = float(r.get("dailyAverageWorkingHours", 8))
        dissatisfaction = 5 - sat
        load_score      = load - 1
        overtime_bonus  = 1 if ot > 20 else 0
        hours_bonus     = 1 if hrs > 9 else 0
        scores.append(dissatisfaction + load_score + overtime_bonus + hours_bonus)

    scores = np.array(scores)
    labels = np.where(scores <= 3, 0, np.where(scores <= 6, 1, 2))
    names  = {0: "好缺", 1: "普通", 2: "屎缺"}
    for cls, name in names.items():
        cnt = (labels == cls).sum()
        print(f"    Class {cls} ({name}): {cnt} 筆 ({cnt/len(labels)*100:.1f}%)")


# ─── 主程式 ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="104 爬蟲資料 → LSTM 訓練集")
    parser.add_argument("--input",  default=None, help="指定爬蟲 JSON 路徑")
    parser.add_argument("--merge",  action="store_true", help="合併原始 employee.json")
    parser.add_argument("--output", default=OUT_PATH, help="輸出路徑")
    args = parser.parse_args()

    input_path = args.input or find_latest_crawl_file()
    if not input_path:
        print("[錯誤] 找不到爬蟲資料，請先執行爬蟲或用 --input 指定檔案")
        return

    records = build_dataset(input_path, merge_original=args.merge)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"\n[完成] 資料集已儲存：{args.output}（{len(records)} 筆）")

    print_label_stats(records)
    print("\n下一步：")
    print("  python ml/train_lstm.py --data \"cash dataset/employee_crawled.json\"")


if __name__ == "__main__":
    main()
