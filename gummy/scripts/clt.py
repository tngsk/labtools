# 環境構築（まだしていなければ）
# uv sync
#
# 実行
# uv run python scripts/clt.py

import matplotlib.pyplot as plt
import numpy as np

# simulation_clt.py

n_samples = 100000  # サンプル数（大きいほど滑らかになる）

# 1〜6 が一様に出る乱数（サイコロ）
# shape: (n_samples, )
uniform_1 = np.random.randint(1, 7, size=n_samples)

# サイコロ10個の合計
# shape: (n_samples, 10) を作って、axis=1 で合計
uniform_10 = np.random.randint(1, 7, size=(n_samples, 10)).sum(axis=1)

# サイコロ30個の合計
uniform_30 = np.random.randint(1, 7, size=(n_samples, 30)).sum(axis=1)

# ヒストグラムを並べて表示
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# 1個
axes[0].hist(uniform_1, bins=np.arange(0.5, 6.6, 1), density=True, edgecolor="black")
axes[0].set_title("サイコロ1個の分布（ほぼ一様）")

# 10個合計
axes[1].hist(uniform_10, bins=30, density=True, edgecolor="black")
axes[1].set_title("サイコロ10個の合計の分布（山型）")

# 30個合計
axes[2].hist(uniform_30, bins=40, density=True, edgecolor="black")
axes[2].set_title("サイコロ30個の合計の分布（より正規分布っぽい）")

for ax in axes:
    ax.set_xlabel("値")
    ax.set_ylabel("確率密度")

plt.tight_layout()
plt.show()
