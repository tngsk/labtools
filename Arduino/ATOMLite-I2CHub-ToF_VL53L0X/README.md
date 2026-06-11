# VL53L0X Data Receiver

ToFセンサー VL53L0X のデータ受信・表示・分析ツール

## セットアップ

### 1. 仮想環境の作成・有効化

```bash
# 仮想環境を作成（初回のみ）
python3 -m venv venv

# 仮想環境を有効化
source venv/bin/activate  # macOS/Linux
```

### 2. 必要なパッケージのインストール

```bash
pip install -r requirments.txt
```

## 使用方法

### 基本的な起動方法

```bash
# 仮想環境を有効化
source venv/bin/activate

# 対話式起動（推奨）
python receiver_python.py
```

### その他の起動オプション

```bash
# シリアル接続テスト
python receiver_python.py test

# 自動実行モード（GUIなし、10秒間）
python receiver_python.py auto 10

# 使用方法の表示
python receiver_python.py --help
```

## 動作モード

1. **Normal Mode**: 標準的なリアルタイムプロット表示
2. **Object Identification Mode**: オブジェクト識別機能付き
3. **Object Identification DEBUG Mode**: キャリブレーション用デバッグモード

## シリアルポート

プログラムは自動的にArduino互換のシリアルポートを検出します：
- macOS: `/dev/cu.usbserial-*`, `/dev/cu.usbmodem-*`
- Bluetooth等の不要なポートは自動的に除外されます
- ポートが1つだけの場合は自動選択を提案します
