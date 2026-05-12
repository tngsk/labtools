# 環境構築（まだしていなければ）
# uv sync
#
# 実行
# uv run python rm_anova.py

"""
反復測定分散分析（1要因被験者内）の分析スクリプト。
可視化は visualize モジュールに委譲する。
"""

import numpy as np
import pandas as pd
import pingouin as pg

import visualize as graph

pd.set_option(
    "display.float_format",
    lambda x: np.format_float_positional(x, precision=4, fractional=False, trim="-"),
)
np.set_printoptions(suppress=True, precision=8)


def fmt_p(x):
    if pd.isna(x):
        return x
    return np.format_float_positional(x, precision=4, fractional=False, trim="-")


def run_analysis(df: pd.DataFrame, meta: dict) -> None:
    """
    反復測定分散分析を実行する。

    Parameters:
        df  : ロング形式の DataFrame
        meta: 分析設定。以下のキーを持つ dict
              - subject : 被験者 ID 列名
              - dv      : 従属変数列名
              - within  : 被験者内要因列名（str または list[str]）
    """
    within = meta["within"]
    primary_within = within[0] if isinstance(within, list) else within

    # 1. 記述統計
    print("\n【記述統計】")
    print(df.groupby(within)[meta["dv"]].agg(["mean", "std", "count"]).round(3))

    # 2. グラフ保存
    graph.sphericity_check(df, meta["subject"], primary_within, meta["dv"]).write_image(
        "assets/00_sphericity_check.png", scale=2
    )
    graph.individual_trends(
        df, meta["subject"], primary_within, meta["dv"]
    ).write_image("assets/01_individual_trends.png", scale=2)
    graph.summary_plot(df, within, meta["dv"]).write_image(
        "assets/02_summary_plot.png", scale=2
    )
    print(
        "  → グラフを保存しました (assets/00_sphericity_check.png, assets/01_individual_trends.png, assets/02_summary_plot.png)"
    )

    # 3. 反復測定分散分析（球面性検定・GG補正込み）
    print("\n【反復測定分散分析】")
    aov = pg.rm_anova(
        data=df,
        dv=meta["dv"],
        within=within,
        subject=meta["subject"],
        correction=True,  # type: ignore[arg-type]
    )
    for col in ["p-unc", "p-GG-corr", "p-spher", "p_unc", "p_GG_corr", "p_spher"]:
        if col in aov.columns:
            aov[col] = aov[col].map(fmt_p)
    print(aov.T.to_string(header=False))

    # 4. 多重比較（Bonferroni vs Holm）
    print("\n【多重比較の比較：補正手法による p 値の変動】")
    ph_bonf = pg.pairwise_tests(
        data=df, dv=meta["dv"], within=within, subject=meta["subject"], padjust="bonf"
    )
    ph_holm = pg.pairwise_tests(
        data=df, dv=meta["dv"], within=within, subject=meta["subject"], padjust="holm"
    )

    def get_col(frame: pd.DataFrame, options: list[str]) -> str | None:
        return next((o for o in options if o in frame.columns), None)

    p_unc_col = get_col(ph_bonf, ["p-unc", "p_unc"])
    p_corr_col = get_col(ph_bonf, ["p-corr", "p_corr"])

    if p_unc_col and p_corr_col:
        comparison = pd.DataFrame(
            {
                "Contrast": ph_bonf["Contrast"],
                "A": ph_bonf["A"],
                "B": ph_bonf["B"],
                "p_uncorr": ph_bonf[p_unc_col].map(fmt_p),
                "p_Bonf": ph_bonf[p_corr_col].map(fmt_p),
                "p_Holm": ph_holm[p_corr_col].map(fmt_p),
                "hedges": ph_bonf["hedges"].round(3),
            }
        )
        print(comparison.to_string(index=False))
    else:
        print(
            f"Error: p 値カラムが見つかりません。現行カラム: {ph_bonf.columns.tolist()}"
        )


if __name__ == "__main__":
    META = {
        "filename": "gummy_data.csv",
        "subject": "ID",
        "dv": "おいしさ",
        "within": ["グミ番号"],
    }

    try:
        data = pd.read_csv(META["filename"])
    except FileNotFoundError:
        print(f"Error: {META['filename']} が見つかりません。")
        raise SystemExit(1)

    print(f"【分析開始】 要因: {META['within']} / 測定値: {META['dv']}")
    run_analysis(data, META)
