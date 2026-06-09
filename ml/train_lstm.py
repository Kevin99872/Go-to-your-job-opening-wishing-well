"""
屎缺偵測 LSTM 三分類模型
Labels: 0=好缺, 1=普通, 2=屎缺
Data: cash dataset/employee.json
"""

import json
import re
import os
import pickle
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
from sklearn.metrics import (confusion_matrix, classification_report,
                              roc_curve, auc)
import pandas as pd
import matplotlib
matplotlib.use("Agg")          # 無 GUI 環境也能存圖
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns

# ─── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR   = os.path.join(BASE_DIR, "cash dataset")
MODEL_DIR  = os.path.join(BASE_DIR, "ml", "saved_model")
CHARTS_DIR = os.path.join(BASE_DIR, "ml", "charts")
os.makedirs(MODEL_DIR,  exist_ok=True)
os.makedirs(CHARTS_DIR, exist_ok=True)

# ─── 中文字型設定（Windows / Linux 自動偵測）────────────────────────────────
def _setup_font():
    """嘗試找可用的中文字型，找不到則用英文 fallback。"""
    candidates = [
        "Microsoft JhengHei", "Microsoft YaHei", "Noto Sans CJK TC",
        "WenQuanYi Micro Hei", "SimHei", "PingFang TC",
    ]
    available = {f.name for f in fm.fontManager.ttflist}
    for font in candidates:
        if font in available:
            plt.rcParams["font.family"] = font
            return font
    plt.rcParams["font.family"] = "DejaVu Sans"
    return "DejaVu Sans"

_FONT = _setup_font()
plt.rcParams["axes.unicode_minus"] = False   # 負號正常顯示

# ─── CLI 參數（支援自訂資料集路徑）────────────────────────────────────────────
import argparse as _argparse
_parser = _argparse.ArgumentParser(add_help=False)
_parser.add_argument("--data", default=None,
                     help="訓練資料路徑（預設: cash dataset/employee.json）")
_args, _ = _parser.parse_known_args()
CUSTOM_DATA_PATH = _args.data  # None 表示用預設

SEQ_LEN    = 5      # LSTM 時間窗長度
EPOCHS     = 120
BATCH_SIZE = 16
SEED       = 42
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
    path = CUSTOM_DATA_PATH or os.path.join(DATA_DIR, "employee.json")
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


# ─── 6. 評估圖表 ──────────────────────────────────────────────────────────────

LABEL_NAMES_LIST = ["好缺", "普通", "屎缺"]

def plot_training_history(history, save_dir: str):
    """圖1：訓練曲線（Accuracy & Loss）"""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    fig.suptitle("LSTM Training History", fontsize=14, fontweight="bold")

    # Accuracy
    ax = axes[0]
    ax.plot(history.history["accuracy"],     label="Train Acc", color="#3498db", linewidth=2)
    ax.plot(history.history["val_accuracy"], label="Val Acc",   color="#e74c3c", linewidth=2, linestyle="--")
    best_ep  = int(np.argmax(history.history["val_accuracy"]))
    best_acc = history.history["val_accuracy"][best_ep]
    ax.axvline(best_ep, color="gray", linestyle=":", alpha=0.7)
    ax.annotate(f"Best\nEp{best_ep}\n{best_acc:.3f}",
                xy=(best_ep, best_acc), xytext=(best_ep+2, best_acc-0.05),
                fontsize=8, color="gray",
                arrowprops=dict(arrowstyle="->", color="gray"))
    ax.set_title("Accuracy"); ax.set_xlabel("Epoch"); ax.set_ylabel("Accuracy")
    ax.legend(); ax.grid(alpha=0.3)

    # Loss
    ax = axes[1]
    ax.plot(history.history["loss"],     label="Train Loss", color="#2ecc71", linewidth=2)
    ax.plot(history.history["val_loss"], label="Val Loss",   color="#e67e22", linewidth=2, linestyle="--")
    ax.set_title("Loss"); ax.set_xlabel("Epoch"); ax.set_ylabel("Loss")
    ax.legend(); ax.grid(alpha=0.3)

    path = os.path.join(save_dir, "01_training_history.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖1] 訓練曲線 → {path}")


def plot_confusion_matrix(y_true, y_pred, save_dir: str):
    """圖2：混淆矩陣"""
    cm = confusion_matrix(y_true, y_pred)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)   # 正規化

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Confusion Matrix", fontsize=14, fontweight="bold")

    for ax, data, fmt, title in zip(
        axes,
        [cm, cm_norm],
        ["d", ".2f"],
        ["Count", "Normalized (Row %)"]
    ):
        sns.heatmap(
            data, annot=True, fmt=fmt, cmap="Blues",
            xticklabels=LABEL_NAMES_LIST, yticklabels=LABEL_NAMES_LIST,
            ax=ax, linewidths=0.5, linecolor="white",
            annot_kws={"size": 13, "weight": "bold"}
        )
        ax.set_title(title, fontsize=11)
        ax.set_xlabel("Predicted Label", fontsize=10)
        ax.set_ylabel("True Label", fontsize=10)

    path = os.path.join(save_dir, "02_confusion_matrix.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖2] 混淆矩陣 → {path}")


def plot_classification_report(y_true, y_pred, save_dir: str):
    """圖3：Per-class Precision / Recall / F1 長條圖"""
    report = classification_report(y_true, y_pred,
                                   target_names=LABEL_NAMES_LIST,
                                   output_dict=True)
    metrics = ["precision", "recall", "f1-score"]
    x  = np.arange(len(LABEL_NAMES_LIST))
    w  = 0.25
    colors = ["#3498db", "#2ecc71", "#e74c3c"]

    fig, ax = plt.subplots(figsize=(9, 5))
    for i, (metric, color) in enumerate(zip(metrics, colors)):
        vals = [report[cls][metric] for cls in LABEL_NAMES_LIST]
        bars = ax.bar(x + i * w, vals, width=w, label=metric.capitalize(),
                      color=color, alpha=0.85, edgecolor="white")
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title(f"Per-class Metrics  (Macro F1={report['macro avg']['f1-score']:.3f})",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x + w)
    ax.set_xticklabels(LABEL_NAMES_LIST, fontsize=11)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score"); ax.legend(); ax.grid(axis="y", alpha=0.3)

    # 整體 accuracy 標註
    acc = report["accuracy"]
    ax.text(0.98, 0.97, f"Accuracy: {acc:.3f}", transform=ax.transAxes,
            ha="right", va="top", fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="#ecf0f1", ec="gray"))

    path = os.path.join(save_dir, "03_classification_report.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖3] 分類指標 → {path}")


def plot_roc_curves(model, X_val, y_val, save_dir: str):
    """圖4：One-vs-Rest ROC 曲線"""
    from sklearn.preprocessing import label_binarize
    y_bin  = label_binarize(y_val, classes=[0, 1, 2])
    y_prob = model.predict(X_val, verbose=0)

    colors = ["#3498db", "#f39c12", "#e74c3c"]
    fig, ax = plt.subplots(figsize=(7, 6))

    for i, (cls, color) in enumerate(zip(LABEL_NAMES_LIST, colors)):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_prob[:, i])
        roc_auc = auc(fpr, tpr)
        ax.plot(fpr, tpr, color=color, linewidth=2,
                label=f"{cls}  (AUC = {roc_auc:.3f})")

    ax.plot([0, 1], [0, 1], "k--", alpha=0.4, linewidth=1)
    ax.set_title("ROC Curve (One-vs-Rest)", fontsize=13, fontweight="bold")
    ax.set_xlabel("False Positive Rate"); ax.set_ylabel("True Positive Rate")
    ax.legend(loc="lower right"); ax.grid(alpha=0.3)

    path = os.path.join(save_dir, "04_roc_curves.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖4] ROC 曲線 → {path}")


def plot_label_distribution(y_seq, y_train, y_val, save_dir: str):
    """圖5：標籤分佈（全資料 / Train / Val）"""
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    fig.suptitle("Label Distribution", fontsize=14, fontweight="bold")
    colors = ["#2ecc71", "#f39c12", "#e74c3c"]

    for ax, data, title in zip(
        axes,
        [y_seq, y_train, y_val],
        ["All Data", "Train", "Validation"]
    ):
        unique, counts = np.unique(data, return_counts=True)
        bars = ax.bar([LABEL_NAMES_LIST[u] for u in unique],
                      counts, color=[colors[u] for u in unique],
                      edgecolor="white", linewidth=1.5)
        for bar, cnt in zip(bars, counts):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() + 0.3,
                    f"{cnt}\n({cnt/len(data)*100:.1f}%)",
                    ha="center", va="bottom", fontsize=9)
        ax.set_title(f"{title}  (n={len(data)})")
        ax.set_ylabel("Count"); ax.grid(axis="y", alpha=0.3)

    path = os.path.join(save_dir, "05_label_distribution.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖5] 標籤分佈 → {path}")


def plot_feature_importance(model, save_dir: str):
    """圖6：輸入層權重絕對值平均（近似特徵重要性）"""
    # 取第一層 LSTM 的 kernel 權重（input → hidden）
    lstm_layer = None
    for layer in model.layers:
        if "lstm" in layer.name.lower():
            lstm_layer = layer
            break
    if lstm_layer is None:
        return

    weights = lstm_layer.get_weights()
    if not weights:
        return

    # kernel shape: (n_features, 4 * n_units) — 4 gates
    kernel = weights[0]   # (n_features, 4 * units)
    importance = np.abs(kernel).mean(axis=1)   # (n_features,)

    # 排序
    order = np.argsort(importance)[::-1]
    sorted_feats = [FEATURE_COLS[i] for i in order]
    sorted_vals  = importance[order]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(sorted_feats[::-1], sorted_vals[::-1],
                   color=plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, len(sorted_feats))),
                   edgecolor="white")
    for bar, v in zip(bars, sorted_vals[::-1]):
        ax.text(v + 0.001, bar.get_y() + bar.get_height()/2,
                f"{v:.4f}", va="center", fontsize=8)

    ax.set_title("Feature Importance\n(LSTM Input Kernel |Weight| Mean)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("Mean |Weight|"); ax.grid(axis="x", alpha=0.3)

    path = os.path.join(save_dir, "06_feature_importance.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖6] 特徵重要性 → {path}")


def plot_probability_distribution(model, X_val, y_val, save_dir: str):
    """圖7：各類別預測機率分佈（violin plot）"""
    y_prob = model.predict(X_val, verbose=0)
    colors = ["#2ecc71", "#f39c12", "#e74c3c"]

    fig, axes = plt.subplots(1, 3, figsize=(13, 5))
    fig.suptitle("Predicted Probability Distribution per True Class",
                 fontsize=13, fontweight="bold")

    for i, (cls, ax) in enumerate(zip(LABEL_NAMES_LIST, axes)):
        data_by_true = [y_prob[y_val == j, i] for j in range(3)]
        parts = ax.violinplot(data_by_true, positions=[0, 1, 2],
                              showmedians=True, showextrema=True)
        for pc, color in zip(parts["bodies"], colors):
            pc.set_facecolor(color); pc.set_alpha(0.7)
        parts["cmedians"].set_color("black")
        ax.set_title(f"P({cls})")
        ax.set_xticks([0, 1, 2]); ax.set_xticklabels(LABEL_NAMES_LIST)
        ax.set_ylabel("Probability"); ax.set_ylim(0, 1.05)
        ax.axhline(1/3, color="gray", linestyle="--", alpha=0.5, linewidth=1)
        ax.grid(axis="y", alpha=0.3)

    path = os.path.join(save_dir, "07_probability_distribution.png")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  [圖7] 機率分佈 → {path}")


def generate_all_charts(model, history, X_val, y_val, y_seq, y_train):
    """呼叫所有圖表函式，存至 ml/charts/"""
    print(f"\n[評估圖表] 字型：{_FONT}，輸出至：{CHARTS_DIR}")
    y_pred = np.argmax(model.predict(X_val, verbose=0), axis=1)

    plot_training_history(history, CHARTS_DIR)
    plot_confusion_matrix(y_val, y_pred, CHARTS_DIR)
    plot_classification_report(y_val, y_pred, CHARTS_DIR)
    plot_roc_curves(model, X_val, y_val, CHARTS_DIR)
    plot_label_distribution(y_seq, y_train, y_val, CHARTS_DIR)
    plot_feature_importance(model, CHARTS_DIR)
    plot_probability_distribution(model, X_val, y_val, CHARTS_DIR)

    print(f"\n  全部 7 張圖已儲存至：{CHARTS_DIR}")


# ─── 7. 主流程 ────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("屎缺偵測 LSTM 三分類訓練")
    print("=" * 60)

    # --- 載入 ---
    print("\n[1/7] 載入資料...")
    df = load_employee_data()
    print(f"  employee.json: {len(df)} 筆")

    # --- 標籤 ---
    print("\n[2/7] 生成標籤...")
    labels = generate_labels(df)
    unique, counts = np.unique(labels, return_counts=True)
    label_names = {0: "好缺", 1: "普通", 2: "屎缺"}
    for u, c in zip(unique, counts):
        print(f"  Class {u} ({label_names[u]}): {c} 筆 ({c/len(labels)*100:.1f}%)")

    # --- 特徵矩陣 ---
    print("\n[3/7] 特徵標準化...")
    X_raw = df[FEATURE_COLS].values.astype(np.float32)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_raw)
    print(f"  特徵數: {X_scaled.shape[1]}, 樣本數: {X_scaled.shape[0]}")

    # --- 序列 ---
    print(f"\n[4/7] 建立序列 (seq_len={SEQ_LEN})...")
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
    print("\n[5/7] 建立 LSTM 模型...")
    model = build_model(seq_len=SEQ_LEN, n_features=len(FEATURE_COLS))
    model.summary(print_fn=lambda s: print("  " + s))

    # --- 訓練 ---
    print(f"\n[6/7] 訓練 (最多 {EPOCHS} epochs)...")
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
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)

    # 儲存特徵欄位與序列長度設定
    config = {"seq_len": SEQ_LEN, "feature_cols": FEATURE_COLS, "label_names": label_names}
    with open(os.path.join(MODEL_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print(f"\n模型已儲存至: {MODEL_DIR}/best_lstm.keras")
    print("Scaler 已儲存至: scaler.pkl")
    print("設定已儲存至: config.json")

    # --- 評估圖表 [7/7] ---
    print(f"\n[7/7] 產生評估圖表...")
    try:
        generate_all_charts(
            model    = model,
            history  = history,
            X_val    = X_val,
            y_val    = y_val,
            y_seq    = y_seq,
            y_train  = y_train,
        )
    except Exception as e:
        print(f"  [warn] 圖表產生失敗：{e}")

    print("\n完成！")
    return model, history


if __name__ == "__main__":
    main()
