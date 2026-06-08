"""
屎缺偵測推論腳本
Usage: python predict.py
"""

import json, pickle, os, warnings
import numpy as np
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, "ml", "saved_model")

model = tf.keras.models.load_model(os.path.join(MODEL_DIR, "best_lstm.keras"))
with open(os.path.join(MODEL_DIR, "scaler.pkl"), "rb") as f:
    scaler = pickle.load(f)
with open(os.path.join(MODEL_DIR, "config.json"), encoding="utf-8") as f:
    config = json.load(f)

SEQ_LEN = config["seq_len"]
FEATURE_COLS = config["feature_cols"]
LABEL_NAMES = {int(k): v for k, v in config["label_names"].items()}


def predict_job(history_records: list[dict]) -> dict:
    """
    history_records: 最近 SEQ_LEN 筆工作紀錄的 list，每筆包含以下欄位:
        relevantExperience, currentTenure, monthlyBaseSalary,
        monthlyBonus, totalAnnualCompensation, dailyAverageWorkingHours,
        monthlyOvertime, overtimeFrequency

    Returns: {"label": int, "class": str, "probabilities": dict}
    """
    if len(history_records) < SEQ_LEN:
        raise ValueError(f"需要至少 {SEQ_LEN} 筆紀錄，目前只有 {len(history_records)} 筆")

    rows = []
    for r in history_records[-SEQ_LEN:]:
        row = [float(r.get(col, 0)) for col in FEATURE_COLS]
        rows.append(row)

    arr = np.array(rows, dtype=np.float32)
    arr_scaled = scaler.transform(arr)
    seq = arr_scaled.reshape(1, SEQ_LEN, len(FEATURE_COLS))

    probs = model.predict(seq, verbose=0)[0]
    label = int(np.argmax(probs))

    return {
        "label": label,
        "class": LABEL_NAMES[label],
        "probabilities": {LABEL_NAMES[i]: float(f"{probs[i]:.4f}") for i in range(3)},
    }


# ─── 示範推論 ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== 屎缺偵測推論示範 ===\n")

    # 範例1: 典型屎缺 (高工時、高加班、低薪)
    shit_job = [
        {"relevantExperience":1,"currentTenure":0.5,"monthlyBaseSalary":3.5,
         "monthlyBonus":0,"totalAnnualCompensation":42,"dailyAverageWorkingHours":11,
         "monthlyOvertime":40,"overtimeFrequency":5},
    ] * SEQ_LEN  # 重複 SEQ_LEN 次模擬連續紀錄

    r1 = predict_job(shit_job)
    print(f"[屎缺情境] 結果: {r1['class']} (label={r1['label']})")
    print(f"  機率: {r1['probabilities']}\n")

    # 範例2: 典型好缺 (正常工時、高薪、低加班)
    good_job = [
        {"relevantExperience":5,"currentTenure":2,"monthlyBaseSalary":12,
         "monthlyBonus":5,"totalAnnualCompensation":180,"dailyAverageWorkingHours":8,
         "monthlyOvertime":2,"overtimeFrequency":1},
    ] * SEQ_LEN

    r2 = predict_job(good_job)
    print(f"[好缺情境] 結果: {r2['class']} (label={r2['label']})")
    print(f"  機率: {r2['probabilities']}\n")

    # 範例3: 普通
    normal_job = [
        {"relevantExperience":3,"currentTenure":1,"monthlyBaseSalary":6,
         "monthlyBonus":1,"totalAnnualCompensation":80,"dailyAverageWorkingHours":9,
         "monthlyOvertime":15,"overtimeFrequency":3},
    ] * SEQ_LEN

    r3 = predict_job(normal_job)
    print(f"[普通情境] 結果: {r3['class']} (label={r3['label']})")
    print(f"  機率: {r3['probabilities']}\n")
