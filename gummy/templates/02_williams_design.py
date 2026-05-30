"""
Williamsデザインを用いたバランス型ラテン方格生成のテンプレートです。
実験の提示順序を割り当て、順序効果（キャリーオーバー効果）を相殺します。
"""

import os
import secrets
from datetime import datetime
import pandas as pd


def generate_williams_design(conditions):
    """
    Williams デザインによるバランス型ラテン方格を生成します。

    Parameters:
        conditions: 条件のリスト（例: ['A', 'B', 'C', 'D']）
    Returns:
        list: バランスされた順序のリストのリスト
    """
    n = len(conditions)
    if n < 2:
        return [list(conditions)]

    rows = []
    for i in range(n):
        row = [0] * n
        for j in range(n):
            if j % 2 == 0:
                row[j] = (i + j // 2) % n
            else:
                row[j] = (i - (j // 2 + 1)) % n
        rows.append(row)

    if n % 2 == 1:
        rows += [list(reversed(r)) for r in rows]

    return [[conditions[idx] for idx in r] for r in rows]


def create_experiment_sheet(
    n_participants,
    conditions,
    item_label="Condition",
    score_label="Score",
    output_csv=True,
    filename_prefix="experiment_sheet",
):
    """
    実験用の順序割り当て表を作成し、必要に応じてCSVに出力します。

    Parameters:
        n_participants (int): 参加者数
        conditions (list): 条件のリスト
        item_label (str): CSVの条件列名
        score_label (str): CSVの評価列名
        output_csv (bool): CSVファイルとして出力するかどうか
        filename_prefix (str): 出力ファイル名のプレフィックス
    """
    orders = generate_williams_design(conditions)
    # 参加者数分だけ繰り返しパターンを生成
    selected = (orders * ((n_participants // len(orders)) + 1))[:n_participants]

    # バランスを保ったまま順序をシャッフル
    secrets.SystemRandom().shuffle(selected)

    n_cond = len(conditions)

    # --- サマリーの表示 ---
    summary_data = {"Participant_ID": [f"S{i + 1:02d}" for i in range(n_participants)]}
    for j in range(n_cond):
        summary_data[f"Order_{j + 1}"] = [o[j] for o in selected]
    summary_data["Full_Sequence"] = [" -> ".join(o) for o in selected]

    summary = pd.DataFrame(summary_data)
    print("【順序割り当てサマリー】")
    print(summary.to_string(index=False))

    print("\n【バランスチェック】")
    for j in range(n_cond):
        pos = f"Order_{j + 1}"
        counts = summary[pos].value_counts().sort_index()
        print(f"  {pos}: " + " | ".join(f"{g}={c}" for g, c in counts.items()))

    # --- CSV出力 ---
    if output_csv:
        rows = []
        for i, order in enumerate(selected):
            for pos, cond in enumerate(order, 1):
                rows.append(
                    {
                        "Participant_ID": f"S{i + 1:02d}",
                        "Presentation_Order": pos,
                        item_label: cond,
                        score_label: "",
                    }
                )
        sheet = pd.DataFrame(rows)
        fname = f"{os.path.basename(filename_prefix)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        sheet.to_csv(fname, index=False, encoding="utf-8-sig")
        print(f"\n実験用記録シートを '{fname}' として保存しました。")

    return summary


if __name__ == "__main__":
    # 実行例：8名 × 4条件の実験シート作成
    create_experiment_sheet(
        n_participants=8,
        conditions=["Cond_A", "Cond_B", "Cond_C", "Cond_D"],
        item_label="Target_Item",
        score_label="Rating_1_to_7",
    )
