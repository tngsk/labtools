"""
中心極限定理（Central Limit Theorem; CLT）のシミュレーションのテンプレートです。
サイコロを振った回数（1個、10個、30個）によって、
その合計値の分布がどのように正規分布に近づくかをシミュレーションして可視化します。
"""

import matplotlib.pyplot as plt
import numpy as np
import os

def simulate_clt(n_samples=100000, output_file="clt_simulation_result.png"):
    """
    中心極限定理のシミュレーションを実行し、グラフを保存します。

    Parameters:
        n_samples (int): サンプル数。大きいほど滑らかな分布になります。
        output_file (str): 保存する画像ファイル名。
    """
    print(f"サンプル数 {n_samples} でシミュレーションを開始します...")

    # 1〜6 が一様に出る乱数（サイコロ1個）
    uniform_1 = np.random.randint(1, 7, size=n_samples)

    # サイコロ10個の合計
    uniform_10 = np.random.randint(1, 7, size=(n_samples, 10)).sum(axis=1)

    # サイコロ30個の合計
    uniform_30 = np.random.randint(1, 7, size=(n_samples, 30)).sum(axis=1)

    # ヒストグラムを並べて表示するための設定
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    # 1個
    axes[0].hist(uniform_1, bins=np.arange(0.5, 6.6, 1), density=True, edgecolor="black")
    axes[0].set_title("Dice x 1 (Uniform)") # 日本語フォントが入っていない環境への配慮で英語に変更

    # 10個合計
    axes[1].hist(uniform_10, bins=30, density=True, edgecolor="black")
    axes[1].set_title("Sum of 10 Dice")

    # 30個合計
    axes[2].hist(uniform_30, bins=40, density=True, edgecolor="black")
    axes[2].set_title("Sum of 30 Dice (Approaching Normal)")

    for ax in axes:
        ax.set_xlabel("Value")
        ax.set_ylabel("Probability Density")

    plt.tight_layout()

    # グラフの保存
    os.makedirs(os.path.dirname(os.path.abspath(output_file)) or '.', exist_ok=True)
    plt.savefig(output_file)
    print(f"シミュレーション結果を {output_file} に保存しました。")
    plt.close()

if __name__ == "__main__":
    # 実行例
    simulate_clt(n_samples=100000, output_file="clt_result.png")
