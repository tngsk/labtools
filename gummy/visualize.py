# 環境構築（まだしていなければ）
# uv sync
#
# このファイルは rm_anova.py から import して使用するモジュールです

"""
可視化モジュール。
各関数は DataFrame と列名を受け取り、plotly の Figure を返す。
副作用（保存・表示）は呼び出し側で行う。
"""

from itertools import combinations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def individual_trends(
    df: pd.DataFrame, subject: str, within: str, dv: str
) -> go.Figure:
    """被験者ごとの個人内変化を折れ線グラフで返す"""
    fig = px.line(
        df,
        x=within,
        y=dv,
        color=subject,
        markers=True,
        title=f"個人別の傾向: {dv}",
    )
    fig.update_layout(showlegend=False, yaxis_title=dv)
    fig.update_traces(opacity=0.5)
    return fig


def summary_plot(df: pd.DataFrame, within: str | list[str], dv: str) -> go.Figure:
    """平均値 ± 標準誤差（一要因）または交互作用プロット（二要因）を返す"""
    if isinstance(within, list) and len(within) > 1:
        w1, w2 = within[0], within[1]
        stats = (
            df.groupby([w1, w2])[dv]
            .agg(mean="mean", std="std", count="count")
            .reset_index()
        )
        stats["sem"] = stats["std"] / np.sqrt(stats["count"])
        fig = px.bar(
            stats,
            x=w1,
            y="mean",
            color=w2,
            error_y="sem",
            title="交互作用プロット",
            labels={"mean": dv},
        )
    else:
        w = within[0] if isinstance(within, list) else within
        stats = (
            df.groupby(w)[dv].agg(mean="mean", std="std", count="count").reset_index()
        )
        stats["sem"] = stats["std"] / np.sqrt(stats["count"])
        fig = px.bar(
            stats,
            x=w,
            y="mean",
            error_y="sem",
            title=f"平均値と標準誤差: {dv}",
            labels={"mean": dv},
        )
    fig.update_layout(yaxis_title=dv)
    return fig


def sphericity_check(df: pd.DataFrame, subject: str, within: str, dv: str) -> go.Figure:
    """全ペアの差分散布図で球面性の視覚的確認を返す"""
    wide = df.pivot(index=subject, columns=within, values=dv)
    conditions = wide.columns.tolist()

    pair_diffs: dict[str, np.ndarray] = {
        f"{c1}-{c2}": wide[c1].to_numpy(dtype=float) - wide[c2].to_numpy(dtype=float)
        for c1, c2 in combinations(conditions, 2)
    }
    pair_vars = {k: float(np.var(v, ddof=1)) for k, v in pair_diffs.items()}
    min_pair = min(pair_vars, key=lambda k: pair_vars[k])
    max_pair = max(pair_vars, key=lambda k: pair_vars[k])
    ref_pair = next(k for k in pair_diffs if k not in (min_pair, max_pair))
    lim = float(max(np.abs(v).max() for v in pair_diffs.values())) + 0.5

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=[
            f"差の分散が小さいペア ({min_pair} vs {ref_pair})"
            f"<br>var={pair_vars[min_pair]:.2f} / ref={pair_vars[ref_pair]:.2f}",
            f"差の分散が大きいペア ({max_pair} vs {ref_pair})"
            f"<br>var={pair_vars[max_pair]:.2f} / ref={pair_vars[ref_pair]:.2f}",
        ],
    )
    for col_idx, (pair, color) in enumerate(
        [(min_pair, "royalblue"), (max_pair, "crimson")], 1
    ):
        fig.add_trace(
            go.Scatter(
                x=pair_diffs[ref_pair].tolist(),
                y=pair_diffs[pair].tolist(),
                mode="markers",
                marker=dict(color=color, size=10, opacity=0.8),
                showlegend=False,
            ),
            row=1,
            col=col_idx,
        )
        fig.update_xaxes(range=[-lim, lim], row=1, col=col_idx)
        fig.update_yaxes(range=[-lim, lim], row=1, col=col_idx)

    fig.add_hline(y=0, line=dict(color="gray", dash="dash", width=1))
    fig.add_vline(x=0, line=dict(color="gray", dash="dash", width=1))
    fig.update_xaxes(title_text=f"差：{ref_pair}")
    fig.update_yaxes(col=1, title_text=f"差：{min_pair}")
    fig.update_yaxes(col=2, title_text=f"差：{max_pair}")
    fig.update_layout(title="球面性の視覚的確認（差の分散が均等か）", height=450)
    return fig
