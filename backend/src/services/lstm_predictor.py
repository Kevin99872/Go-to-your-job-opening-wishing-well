"""
LSTM 本地推論服務
載入 ml/saved_model/ 內的模型，對單筆 104 職缺進行好缺/普通/屎缺分類
"""

import os
import json
import pickle
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 模型目錄：backend/src/services/ → 上三層 = 專案根目錄
_THIS_FILE = os.path.abspath(__file__)                          # .../backend/src/services/lstm_predictor.py
_BACKEND   = os.path.dirname(os.path.dirname(os.path.dirname(_THIS_FILE)))  # .../backend
_ROOT      = os.path.dirname(_BACKEND)                         # 專案根目錄
_MODEL_DIR = os.path.join(_ROOT, "ml", "saved_model")

# 業界薪資參考（與 dataset_builder.py 相同，避免互相依賴）
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

_RED_FLAG_WORDS = [
    "責任制", "無休假", "需配合加班", "假日加班", "輪班",
    "大夜班", "急徵", "立即上班", "高壓",
]
_GREEN_FLAG_WORDS = [
    "準時下班", "不需加班", "週休二日", "彈性上班",
    "股票", "員工股", "年終獎金",
]


class LSTMPredictor:
    """
    載入訓練好的 LSTM 模型，提供單筆或批次職缺預測。

    使用方式：
        predictor = LSTMPredictor()
        result = predictor.predict_from_job({
            "jobTitle": "後端工程師",
            "salaryMin": 50000, "salaryMax": 70000,
            "descSnippet": "...",
            "overtimeHint": 1,
        })
    """

    def __init__(self):
        self._model   = None
        self._scaler  = None
        self._config  = None
        self._ready   = False
        self._load()

    # ─── 載入 ────────────────────────────────────────────────────────────────

    def _load(self):
        model_path  = os.path.join(_MODEL_DIR, "best_lstm.keras")
        scaler_path = os.path.join(_MODEL_DIR, "scaler.pkl")
        config_path = os.path.join(_MODEL_DIR, "config.json")

        missing = [p for p in [model_path, scaler_path, config_path]
                   if not os.path.exists(p)]
        if missing:
            logger.warning(f"LSTM 模型檔案缺失：{missing}，請先執行 train_lstm.py")
            return

        try:
            import tensorflow as tf
            self._model = tf.keras.models.load_model(model_path)

            with open(scaler_path, "rb") as f:
                self._scaler = pickle.load(f)

            with open(config_path, encoding="utf-8") as f:
                self._config = json.load(f)

            self._label_names = {
                int(k): v for k, v in self._config["label_names"].items()
            }
            self._seq_len      = self._config["seq_len"]
            self._feature_cols = self._config["feature_cols"]
            self._ready        = True
            logger.info("LSTM 模型載入成功")

        except Exception as e:
            logger.error(f"LSTM 模型載入失敗：{e}")

    # ─── 公開 API ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    def predict_from_job(self, job: Dict) -> Dict:
        """
        從單筆 104 職缺 dict 預測好缺/普通/屎缺。

        輸入欄位（至少需要薪資其中一項）：
            jobTitle, salaryMin, salaryMax, salaryText,
            descSnippet / fullDescription, overtimeHint

        Returns:
            {
              "label": 0|1|2,
              "class": "好缺"|"普通"|"屎缺",
              "probabilities": {"好缺": 0.xx, "普通": 0.xx, "屎缺": 0.xx},
              "features": {...},   # 推論用的特徵值
              "model": "lstm"
            }
        """
        if not self._ready:
            return {"error": "LSTM 模型尚未載入，請先訓練模型", "model": "lstm"}

        try:
            features = self._extract_features(job)
            record   = [features]   # 單筆 → 複製 seq_len 份模擬序列
            result   = self._predict_sequence(record * self._seq_len)
            result["features"] = features
            return result

        except Exception as e:
            logger.error(f"LSTM 推論失敗：{e}")
            return {"error": str(e), "model": "lstm"}

    def predict_batch(self, jobs: List[Dict]) -> List[Dict]:
        """批次預測"""
        return [self.predict_from_job(j) for j in jobs]

    # ─── 特徵萃取 ────────────────────────────────────────────────────────────

    def _extract_features(self, job: Dict) -> Dict:
        """從 104 職缺 dict 萃取 LSTM 特徵"""
        # ── 薪資（萬元）───────────────────────────────────────────────────
        sal_min = float(job.get("salaryMin", 0) or 0)
        sal_max = float(job.get("salaryMax", 0) or 0)

        # 若原始值 > 1000 表示單位為元，轉萬元
        if sal_min > 1000: sal_min /= 10000
        if sal_max > 1000: sal_max /= 10000

        monthly_salary = (sal_min + sal_max) / 2 if (sal_min + sal_max) > 0 else 0

        # 若仍為 0，嘗試從文字解析
        if monthly_salary == 0:
            monthly_salary = _parse_salary_text(job.get("salaryText", ""))

        annual_comp = monthly_salary * 12

        # ── 加班特徵────────────────────────────────────────────────────────
        ot_hint = int(job.get("overtimeHint", 1))
        desc    = job.get("fullDescription") or job.get("descSnippet") or ""
        red     = sum(1 for w in _RED_FLAG_WORDS  if w in desc)
        green   = sum(1 for w in _GREEN_FLAG_WORDS if w in desc)

        if red >= 2:
            ot_hint = min(ot_hint + 1, 3)

        daily_hours, monthly_ot, ot_freq = _overtime_to_features(ot_hint)

        return {
            "relevantExperience":       0,
            "currentTenure":            0,
            "monthlyBaseSalary":        round(monthly_salary, 3),
            "monthlyBonus":             0,
            "totalAnnualCompensation":  round(annual_comp, 2),
            "dailyAverageWorkingHours": daily_hours,
            "monthlyOvertime":          monthly_ot,
            "overtimeFrequency":        ot_freq,
        }

    # ─── LSTM 推論 ───────────────────────────────────────────────────────────

    def _predict_sequence(self, history_records: List[Dict]) -> Dict:
        """
        history_records: seq_len 筆 feature dict
        """
        import numpy as np

        rows = []
        for r in history_records[-self._seq_len:]:
            row = [float(r.get(col, 0)) for col in self._feature_cols]
            rows.append(row)

        arr        = np.array(rows, dtype=np.float32)
        arr_scaled = self._scaler.transform(arr)
        seq        = arr_scaled.reshape(1, self._seq_len, len(self._feature_cols))

        probs = self._model.predict(seq, verbose=0)[0]
        label = int(probs.argmax())

        return {
            "label":         label,
            "class":         self._label_names[label],
            "probabilities": {
                self._label_names[i]: float(f"{probs[i]:.4f}")
                for i in range(3)
            },
            "model": "lstm",
        }


# ─── 工具函式 ─────────────────────────────────────────────────────────────────

def _parse_salary_text(text: str) -> float:
    """從薪資描述解析月薪（萬元）"""
    if not text:
        return 0.0
    nums = re.findall(r"[\d,]+", text.replace(",", ""))
    nums = [int(n) for n in nums if n]
    if not nums:
        return 0.0
    val = sum(nums) / len(nums)
    if "萬" in text:
        return val
    if val > 1000:      # 元 → 萬元
        return val / 10000
    return val


def _overtime_to_features(hint: int):
    table = {
        0: (8.0,  2, 1),
        1: (8.5,  8, 2),
        2: (9.5, 20, 4),
        3: (11.0,40, 5),
    }
    return table.get(hint, (8.5, 8, 2))


# ─── 單例（供 app.py import） ─────────────────────────────────────────────────
_predictor_instance: Optional[LSTMPredictor] = None

def get_predictor() -> LSTMPredictor:
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = LSTMPredictor()
    return _predictor_instance
