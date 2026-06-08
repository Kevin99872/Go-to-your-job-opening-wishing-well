"""
屎缺偵測 LSTM 三分類模型
Labels: 0=好缺, 1=普通, 2=屎缺
Data: cash dataset/employee.json
"""

import json
import re
import os
import numpy as np
import warnings
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import pandas as pd

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "cash dataset")
MODEL_DIR = os.path.join(BASE_DIR, "ml", "saved_model")
os.makedirs(MODEL_DIR, exist_ok=True)

SEQ_LEN = 5          # LSTM 時間窗長度
EPOCHS = 120
BATCH_SIZE = 16
SEED = 42
tf.random.set_seed(SEED)
np.random.seed(SEED)


# ─── 1. 數值解析工具 ────────────────────────────────────────────────────────────

def parse_numeric(val, fallback=np.nan):
    """處理混合型態欄位: int/float/string/range → float"""
    if val is None or val == "" or val == "-":
        return fallback
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # range like '24-36' or '10-16'
    m = re.match(r'^([\d.]+)\s*[-~]\s*([\d.]+)$', s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    # '<5' or '>30'
    m2 = re.match(r'^[<>≤≥]?\s*([\d.]+)$', s)
    if m2:
        return float(m2.group(1))
    # Chinese text meaning zero/unknown → 0
    zero_words = {'無', '0', '少', '未知', '不加班', 'none', 'no', '-1'}
    if s.lower() in zero_words or s in zero_words:
        return 0.0
    # try direct cast
    try:
        return float(s)
    except ValueError:
        return fallback


def parse_bonus(val):
    """月獎金: 取數值部分，文字描述 → NaN"""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    # plain number or range
    m = re.match(r'^([\d.]+)\s*[-~]\s*([\d.]+)$', s)
    if m:
        return (float(m.group(1)) + float(m.group(2))) / 2
    try:
        return float(s)
    except ValueError:
        return np.nan


def parse_compensation(val):
    """年薪: '160 + option' → 160"""
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip()
    m = re.match(r'^([\d.]+)', s)
    if m:
        return float(m.group(1))
    return np.nan


# ─── 2. 載入與清理 employee.json ─────────────────────────────────────────────

def load_employee_data():
    path = os.path.join(DATA_DIR, "employee.json")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    records = []
    for r in raw:
        rec = {
            "relevantExperience":      parse_numeric(r.get("relevantExperience"), 0),
            "currentTenure":           parse_numeric(r.get("currentTenure"), 0),
            "monthlyBaseSalary":       parse_numeric(r.get("monthlyBaseSalary"), np.nan),
            "monthlyBonus":            parse_bonus(r.get("monthlyBonus")),
            "totalAnnualCompensation": parse_compensation(r.get("totalAnnualCompensation")),
            "dailyAverageWorkingHours":parse_numeric(r.get("dailyAverageWorkingHours"), 8),
            "monthlyOvertime":         parse_numeric(r.get("monthlyOvertime"), 0),
            "overtimeFrequency":       parse_numeric(r.get("overtimeFrequency"), 1),
            # label source
            "jobSatisfaction":         int(r.get("jobSatisfaction", 3)),
            "loading":                 int(r.get("loading", 3)),
            # timestamp for sorting
            "timestamp":               r.get("timestamp", ""),
        }
        records.append(rec)

    df = pd.DataFrame(records)

    # 排序（依回報時間維持時序）
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", format="mixed")
    df = df.sort_values("timestamp").reset_index(drop=True)

    # 填補缺值: monthlyBonus → 0, totalAnnualCompensation 用 monthlyBaseSalary * 12 估計
    df["monthlyBonus"] = df["monthlyBonus"].fillna(0.0)
    mask = df["totalAnnualCompensation"].isna()
    df.loc[mask, "totalAnnualCompensation"] = df.loc[mask, "monthlyBaseSalary"] * 12

    # 仍有缺值的欄位用中位數補
    num_cols = ["relevantExperience","currentTenure","monthlyBaseSalary",
                "totalAnnualCompensation","dailyAverageWorkingHours",
                "monthlyOvertime","overtimeFrequency"]
    for col in num_cols:
        median = df[col].median()
        df[col] = df[col].fillna(median)

    return df


# ─── 3. 標籤生成（屎缺評分） ─────────────────────────────────────────────────

def generate_labels(df):
    """
    綜合評分: 不滿意度(0-4) + 負載度(0-4) + 加班加成(0-2)
    Range 0-10:  0-3 → 好缺(0),  4-6 → 普通(1),  7-10 → 屎缺(2)
    """
    dissatisfaction = 5 - df["jobSatisfaction"]   # 1→4, 5→0
    load_score = df["loading"] - 1                 # 1→0, 5→4
    overtime_bonus = (df["monthlyOvertime"] > 20).astype(int)
    hours_bonus = (df["dailyAverageWorkingHours"] > 9).astype(int)

    score = dissatisfaction + load_score + overtime_bonus + hours_bonus

    labels = pd.cut(score, bins=[-1, 3, 6, 10], labels=[0, 1, 2]).astype(int)
    return labels.values


# ─── 4. 序列化 (Sliding Window) ──────────────────────────────────────────────

FEATURE_COLS = [
    "relevantExperience", "currentTenure", "monthlyBaseSalary",
    "monthlyBonus", "totalAnnualCompensation", "dailyAverageWorkingHours",
    "monthlyOvertime", "overtimeFrequency",
]

def make_sequences(X: np.ndarray, y: np.ndarray, seq_len: int):
    """建立 (N, seq_len, n_features) 序列，標籤取窗口最後一筆"""
    xs, ys = [], []
    for i in range(len(X) - seq_len + 1):
        xs.append(X[i : i + seq_len])
        ys.append(y[i + seq_len - 1])
    return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.int32)


def augment_sequences(X_seq, y_seq, noise_std=0.02, n_copies=3):
    """小資料集加噪增強"""
    augX, augY = [X_seq], [y_seq]
    for _ in range(n_copies):
        noise = np.random.normal(0, noise_std, X_seq.shape).astype(np.float32)
        augX.append(X_seq + noise)
        augY.append(y_seq)
    return np.concatenate(augX), np.concatenate(augY)


# ─── 5. 建立 LSTM 模型 ─────────────────────────────────────────────────────────

def build_model(seq_len: int, n_features: int, n_classes: int = 3) -> keras.Model:
    inp = keras.Input(shape=(seq_len, n_features))

    x = layers.LSTM(64, return_sequences=True)(inp)
    x = layers.Dropout(0.3)(x)
    x = layers.LSTM(32)(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(32, activation="relu")(x)
    x = layers.BatchNormalization()(x)
    out = layers.Dense(n_classes, activation="softmax")(x)

    model = keras.Model(inp, out)
    model.compile(
        optimizer=keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


# ─── 6. 主流程 ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("屎缺偵測 LSTM 三分類訓練")
    print("=" * 60)

    # --- 載入 ---
    print("\n[1/6] 載入資料...")
    df = load_employee_data()
    print(f"  employee.json: {len(df)} 筆")

    # --- 標籤 ---
    print("\n[2/6] 生成標籤...")
    labels = generate_labels(df)
    unique, counts = np.unique(labels, return_counts=True)
    label_names = {0: "好缺", 1: "普通", 2: "屎缺"}
    for u, c in zip(unique, counts):
        print(f"  Class {u} ({label_names[u]}): {c} 筆 ({c/len(labels)*100:.1f}%)")

    # --- 特徵矩陣 ---
    print("\n[3/6] 特徵標準化...")
    X_raw = df[FEATURE_COLS].values.astype(np.float32)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    print(f"  特徵數: {X_scaled.shape[1]}, 樣本數: {X_scaled.shape[0]}")

    # --- 序列 ---
    print(f"\n[4/6] 建立序列 (seq_len={SEQ_LEN})...")
    X_seq, y_seq = make_sequences(X_scaled, labels, SEQ_LEN)
    X_seq, y_seq = augment_sequences(X_seq, y_seq, noise_std=0.02, n_copies=4)
    print(f"  增強後序列數: {len(X_seq)}")

    # --- 分割 ---
    X_train, X_val, y_train, y_val = train_test_split(
        X_seq, y_seq, test_size=0.2, random_state=SEED, stratify=y_seq
    )
    print(f"  Train: {len(X_train)}, Val: {len(X_val)}")

    # class weights 處理不平衡
    class_weights = compute_class_weight("balanced", classes=np.unique(y_train), y=y_train)
    cw_dict = dict(enumerate(class_weights))
    print(f"  Class weights: { {k: f'{v:.2f}' for k, v in cw_dict.items()} }")

    # --- 建模 ---
    print("\n[5/6] 建立 LSTM 模型...")
    model = build_model(seq_len=SEQ_LEN, n_features=len(FEATURE_COLS))
    model.summary(print_fn=lambda s: print("  " + s))

    # --- 訓練 ---
    print(f"\n[6/6] 訓練 (最多 {EPOCHS} epochs)...")
    callbacks = [
        keras.callbacks.EarlyStopping(
            monitor="val_accuracy", patience=20, restore_best_weights=True, verbose=1
        ),
        keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss", factor=0.5, patience=10, min_lr=1e-5, verbose=0
        ),
        keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(MODEL_DIR, "best_lstm.keras"),
            monitor="val_accuracy", save_best_only=True, verbose=0
        ),
    ]

    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        class_weight=cw_dict,
        callbacks=callbacks,
        verbose=1,
    )

    # --- 結果 ---
    val_acc = max(history.history["val_accuracy"])
    print(f"\n最佳 Val Accuracy: {val_acc*100:.1f}%")

    # 儲存 scaler
    import pickle
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    # 儲存特徵欄位與序列長度設定
    config = {"seq_len": SEQ_LEN, "feature_cols": FEATURE_COLS, "label_names": label_names}
    with open(os.path.join(MODEL_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n模型已儲存至: {MODEL_DIR}/best_lstm.keras")
    print("Scaler 已儲存至: scaler.pkl")
    print("設定已儲存至: config.json")
    print("\n完成！")
    return model, history


if __name__ == "__main__":
    main()
