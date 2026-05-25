"""
反復測定分散分析（1要因被験者内）のテンプレートです。
ダミーデータを生成し、分析・可視化までを1つのスクリプトで完結して実行します。
"""

import numpy as np
import pandas as pd
import pingouin as pg
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from itertools import combinations
import os

# --- ヘルパー関数 ---
def fmt_p(x):
    """p値を整形する"""
    if pd.isna(x):
        return x
    return np.format_float_positional(x, precision=4, fractional=False, trim="-")

# --- 可視化関数 ---
def plot_individual_trends(df, subject, within, dv):
    """個人別の傾向を折れ線グラフで描画"""
    fig = px.line(df, x=within, y=dv, color=subject, markers=True, title=f"Individual Trends: {dv}")
    fig.update_layout(showlegend=False, yaxis_title=dv)
    fig.update_traces(opacity=0.5)
    return fig

def plot_summary(df, within, dv):
    """平均値と標準誤差を棒グラフで描画"""
    stats = df.groupby(within)[dv].agg(mean="mean", std="std", count="count").reset_index()
    stats["sem"] = stats["std"] / np.sqrt(stats["count"])
    fig = px.bar(
        stats, x=within, y="mean", error_y="sem",
        title=f"Mean and Standard Error: {dv}", labels={"mean": dv}
    )
    fig.update_layout(yaxis_title=dv)
    return fig

def plot_sphericity_check(df, subject, within, dv):
    """球面性の視覚的確認（ペア間の差の分散）を描画"""
    wide = df.pivot(index=subject, columns=within, values=dv)
    conditions = wide.columns.tolist()

    pair_diffs = {
        f"{c1}-{c2}": wide[c1].to_numpy(dtype=float) - wide[c2].to_numpy(dtype=float)
        for c1, c2 in combinations(conditions, 2)
    }
    pair_vars = {k: float(np.var(v, ddof=1)) for k, v in pair_diffs.items()}

    if not pair_vars:
        return go.Figure()

    min_pair = min(pair_vars, key=lambda k: pair_vars[k])
    max_pair = max(pair_vars, key=lambda k: pair_vars[k])
    ref_pair_candidates = [k for k in pair_diffs if k not in (min_pair, max_pair)]
    ref_pair = ref_pair_candidates[0] if ref_pair_candidates else min_pair

    lim = float(max(np.abs(v).max() for v in pair_diffs.values())) + 0.5

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=[
            f"Min Variance ({min_pair} vs {ref_pair})<br>var={pair_vars[min_pair]:.2f}",
            f"Max Variance ({max_pair} vs {ref_pair})<br>var={pair_vars[max_pair]:.2f}"
        ]
    )
    for col_idx, (pair, color) in enumerate([(min_pair, "royalblue"), (max_pair, "crimson")], 1):
        fig.add_trace(go.Scatter(
            x=pair_diffs[ref_pair].tolist(), y=pair_diffs[pair].tolist(),
            mode="markers", marker=dict(color=color, size=10, opacity=0.8), showlegend=False,
        ), row=1, col=col_idx)
        fig.update_xaxes(range=[-lim, lim], row=1, col=col_idx)
        fig.update_yaxes(range=[-lim, lim], row=1, col=col_idx)

    fig.add_hline(y=0, line=dict(color="gray", dash="dash", width=1))
    fig.add_vline(x=0, line=dict(color="gray", dash="dash", width=1))
    fig.update_layout(title="Sphericity Check (Equality of Variance of Differences)", height=450)
    return fig

# --- メイン分析関数 ---
def run_rm_anova_analysis(df, subject_col, within_col, dv_col, output_dir="assets_template"):
    """反復測定分散分析と可視化の実行"""
    print("--- 1. Descriptive Statistics ---")
    print(df.groupby(within_col)[dv_col].agg(["mean", "std", "count"]).round(3))

    os.makedirs(output_dir, exist_ok=True)

    print("\n--- 2. Visualizations ---")
    try:
        plot_sphericity_check(df, subject_col, within_col, dv_col).write_image(f"{output_dir}/01_sphericity.png")
        plot_individual_trends(df, subject_col, within_col, dv_col).write_image(f"{output_dir}/02_individual.png")
        plot_summary(df, within_col, dv_col).write_image(f"{output_dir}/03_summary.png")
        print(f"Graphs saved to {output_dir}/")
    except Exception as e:
         print(f"Could not save images (kaleido may not be installed): {e}")

    print("\n--- 3. Repeated Measures ANOVA ---")
    aov = pg.rm_anova(data=df, dv=dv_col, within=within_col, subject=subject_col, correction=True)
    for col in ["p-unc", "p-GG-corr", "p-spher", "p_unc", "p_GG_corr", "p_spher"]:
        if col in aov.columns:
            aov[col] = aov[col].map(fmt_p)
    print(aov.T.to_string(header=False))

    print("\n--- 4. Post-hoc Tests (Multiple Comparisons) ---")
    ph_bonf = pg.pairwise_tests(data=df, dv=dv_col, within=within_col, subject=subject_col, padjust="bonf")

    p_unc_col = next((c for c in ["p-unc", "p_unc"] if c in ph_bonf.columns), None)
    p_corr_col = next((c for c in ["p-corr", "p_corr"] if c in ph_bonf.columns), None)

    if p_unc_col and p_corr_col:
        comparison = pd.DataFrame({
            "Contrast": ph_bonf["Contrast"],
            "A": ph_bonf["A"],
            "B": ph_bonf["B"],
            "p_uncorr": ph_bonf[p_unc_col].map(fmt_p),
            "p_Bonf": ph_bonf[p_corr_col].map(fmt_p),
            "hedges": ph_bonf["hedges"].round(3),
        })
        print(comparison.to_string(index=False))

# --- ダミーデータの生成と実行 ---
if __name__ == "__main__":
    np.random.seed(42)
    n_subjects = 10
    conditions = ['Condition_A', 'Condition_B', 'Condition_C']

    # 参加者内効果を持たせたダミーデータ
    data = []
    for i in range(1, n_subjects + 1):
        base_score = np.random.normal(5, 1) # 個人差
        for j, cond in enumerate(conditions):
            # 条件によって平均値を変える (A < B < C)
            score = base_score + (j * 1.5) + np.random.normal(0, 0.5)
            data.append({"Subject_ID": f"S{i:02d}", "Condition": cond, "Score": score})

    dummy_df = pd.DataFrame(data)

    print("【Generated Dummy Data (Head)】")
    print(dummy_df.head())
    print("\n=========================================\n")

    run_rm_anova_analysis(dummy_df, subject_col="Subject_ID", within_col="Condition", dv_col="Score")
