# 環境構築（まだしていなければ）
# uv sync
#
# 実行
# uv run python scripts/williams-latin-square.py

import random
from datetime import datetime

import pandas as pd


def generate_williams_design(conditions):
    """
    Williams デザインによるバランス型ラテン方格を生成する。
    各条件が各位置に均等に出現し、隣接効果も制御される。
    偶数・奇数いずれの条件数にも対応。

    Parameters:
        conditions: 条件のリスト（例: ['A', 'B', 'C', 'D']）

    Returns:
        list: バランスされた順序のリスト
    """
    n = len(conditions)
    if n < 2:
        return [list(conditions)]

    # Williams デザインの構築（偶数: n行、奇数: 2n行）
    rows = []
    for i in range(n):
        row = [0] * n
        for j in range(n):
            if j % 2 == 0:
                row[j] = (i + j // 2) % n
            else:
                row[j] = (i - (j // 2 + 1)) % n
        rows.append(row)

    # 奇数条件の場合、逆順を追加して完全バランスにする
    if n % 2 == 1:
        rows += [list(reversed(r)) for r in rows]

    return [[conditions[idx] for idx in r] for r in rows]


def create_experiment_sheet(
    n_participants, conditions, item_label="条件", score_label="評価", output_csv=True
):
    """
    実験用の順序割り当て表を作成し、CSV で出力する。

    Parameters:
        n_participants: 参加者数
        conditions: 条件のリスト
        item_label: CSV の条件列名（デフォルト: '条件'）
        score_label: CSV の評価列名（デフォルト: '評価'）
        output_csv: CSV ファイルとして出力するか

    Returns:
        DataFrame: 順序割り当て表
    """
    orders = generate_williams_design(conditions)
    selected = (orders * ((n_participants // len(orders)) + 1))[:n_participants]

    # 割り当て前にシャッフルを行う
    # これにより、バランスを維持したまま「誰と誰が同じか」をバラバラにする
    random.shuffle(selected)
    selected = selected[:n_participants]

    # 順序確認表
    n_cond = len(conditions)
    summary = pd.DataFrame(
        {
            "参加者ID": [f"S{i + 1:02d}" for i in range(n_participants)],
            **{f"{j + 1}番目": [o[j] for o in selected] for j in range(n_cond)},
            "順序": [" → ".join(o) for o in selected],
        }
    )
    print("【順序割り当て表】")
    print(summary.to_string(index=False))

    # バランスチェック
    print("\n【バランスチェック】")
    for j in range(n_cond):
        pos = f"{j + 1}番目"
        counts = summary[pos].value_counts().sort_index()
        print(f"  {pos}: " + " | ".join(f"{g}={c}" for g, c in counts.items()))

    # CSV 出力（データ記録用シート）
    if output_csv:
        rows = [
            {
                "参加者ID": f"S{i + 1:02d}",
                "提示順序": pos,
                item_label: cond,
                score_label: "",
            }
            for i, order in enumerate(selected)
            for pos, cond in enumerate(order, 1)
        ]
        sheet = pd.DataFrame(rows)
        fname = f"experiment_sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        sheet.to_csv(fname, index=False, encoding="utf-8-sig")
        print(f"\n実験シートを '{fname}' に保存しました。")

    return summary


# 実行例：9名 × 4種類のグミ
create_experiment_sheet(
    n_participants=9,
    conditions=["A", "B", "C", "D"],
    item_label="グミの種類",
    score_label="評価（1-7）",
)
