# Max/MSP JavaScript移植プラン
## VL53L0X ToF センサー オブジェクト識別システム

### 概要
PythonベースのVL53L0X ToFセンサーオブジェクト識別システムをMax/MSP環境のNode for Maxに移植するためのプラン。

### 前提条件
- Max/MSPがシリアル通信とデータパースを担当
- チャンネルデータ（ch1, ch2, ch3）は取得済み
- 可視化機能は不要
- フィルタリング済みセンサーデータと識別結果が必要

---

## 1. アーキテクチャ設計

### システム構成
```
Max Patch
    ↓ (シリアル受信・パース)
[serial] → [unpack] → [route ch1 ch2 ch3]
    ↓
[node.script sensor_processor.js]
    ↓ (フィルタリング済みデータ + 識別結果)
Max Objects (bang, outlet等)
```

### データフロー
1. Max: シリアルデータ受信・パース
2. JavaScript: フィルタリング・識別処理
3. Max: 結果の活用・出力

---

## 2. JavaScript モジュール構成

### ファイル構造
```
/maxmsp_sensor_system/
  ├── sensor_processor.js      # メインファイル
  ├── sensor_filter.js         # フィルタリングクラス
  ├── object_identifier.js     # 識別クラス
  ├── config_manager.js        # 設定管理クラス
  ├── config.json             # 設定ファイル
  └── README.md               # 使用方法
```

### メインファイル: sensor_processor.js
```javascript
// Max/MSP Node.js インターface
const maxApi = require('max-api');

// 内部モジュール
const SensorFilter = require('./sensor_filter.js');
const ObjectIdentifier = require('./object_identifier.js');
const ConfigManager = require('./config_manager.js');

// 3チャンネル処理
const processors = {
    ch1: new SensorFilter(),
    ch2: new SensorFilter(), 
    ch3: new SensorFilter()
};

const identifier = new ObjectIdentifier();
const config = new ConfigManager();

// Max からのメッセージ受信
maxApi.addHandler('ch1', (distance) => processChannel('ch1', distance));
maxApi.addHandler('ch2', (distance) => processChannel('ch2', distance)); 
maxApi.addHandler('ch3', (distance) => processChannel('ch3', distance));
maxApi.addHandler('load_config', (filepath) => config.loadConfig(filepath));

function processChannel(channel, distance) {
    // フィルタリング
    const filterResult = processors[channel].addMeasurement(distance);
    
    // 識別
    const identifyResult = identifier.identify(filterResult.filtered);
    
    // Max への出力
    maxApi.outlet(`filtered_${channel}`, 
        filterResult.raw, 
        filterResult.filtered, 
        filterResult.stable
    );
    
    maxApi.outlet(`identified_${channel}`, 
        identifyResult.object || 'Unknown',
        identifyResult.confidence,
        identifyResult.inRange ? 1 : 0
    );
}
```

### フィルタリングモジュール: sensor_filter.js
```javascript
class SensorFilter {
    constructor(options = {}) {
        this.buffer = [];
        this.maxBuffer = options.bufferSize || 10;
        this.minSamples = options.minSamples || 5;
        this.stableThreshold = options.stableThreshold || 1.0;
    }

    addMeasurement(distance) {
        if (distance === null || distance === undefined || isNaN(distance)) {
            return {
                raw: distance,
                filtered: null,
                stable: false
            };
        }

        this.buffer.push(distance);
        if (this.buffer.length > this.maxBuffer) {
            this.buffer.shift();
        }
        
        return {
            raw: distance,
            filtered: this.getFilteredValue(),
            stable: this.isStable()
        };
    }

    getFilteredValue() {
        if (this.buffer.length >= this.minSamples) {
            const recent = this.buffer.slice(-this.minSamples);
            return recent.reduce((a, b) => a + b) / recent.length;
        }
        return this.buffer[this.buffer.length - 1] || null;
    }

    isStable() {
        if (this.buffer.length < this.minSamples) return false;
        
        const recent = this.buffer.slice(-this.minSamples);
        const mean = recent.reduce((a, b) => a + b) / recent.length;
        const variance = recent.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / recent.length;
        const stdDev = Math.sqrt(variance);
        
        return stdDev < this.stableThreshold;
    }

    reset() {
        this.buffer = [];
    }

    updateConfig(config) {
        this.maxBuffer = config.bufferSize || this.maxBuffer;
        this.minSamples = config.minSamples || this.minSamples;
        this.stableThreshold = config.stableThreshold || this.stableThreshold;
    }
}

module.exports = SensorFilter;
```

### 識別モジュール: object_identifier.js
```javascript
class ObjectIdentifier {
    constructor(database = null) {
        this.objectDatabase = database || {
            'ObjectA': { min: 13.1, max: 13.5, name: 'ObjectA' },
            'ObjectB': { min: 15.5, max: 15.9, name: 'ObjectB' },
            'ObjectC': { min: 18.0, max: 18.4, name: 'ObjectC' }
        };
    }

    identify(distance) {
        if (distance === null || distance === undefined || isNaN(distance)) {
            return { 
                object: null, 
                confidence: 0, 
                inRange: false 
            };
        }

        let bestMatch = null;
        let bestConfidence = 0;

        for (const [objId, objData] of Object.entries(this.objectDatabase)) {
            if (distance >= objData.min && distance <= objData.max) {
                const center = (objData.min + objData.max) / 2;
                const range = objData.max - objData.min;
                const confidence = 1.0 - Math.abs(distance - center) / (range / 2);

                if (confidence > bestConfidence) {
                    bestMatch = objData.name;
                    bestConfidence = confidence;
                }
            }
        }

        return {
            object: bestMatch,
            confidence: Math.round(bestConfidence * 100) / 100, // 小数点2桁
            inRange: bestMatch !== null
        };
    }

    updateDatabase(newDatabase) {
        this.objectDatabase = newDatabase;
    }

    addObject(objId, minDist, maxDist, name) {
        this.objectDatabase[objId] = {
            min: minDist,
            max: maxDist,
            name: name || objId
        };
    }

    removeObject(objId) {
        delete this.objectDatabase[objId];
    }

    getObjectList() {
        return Object.keys(this.objectDatabase);
    }
}

module.exports = ObjectIdentifier;
```

### 設定管理モジュール: config_manager.js
```javascript
const fs = require('fs');
const path = require('path');

class ConfigManager {
    constructor(configPath = './config.json') {
        this.configPath = configPath;
        this.config = this.loadDefaultConfig();
    }

    loadDefaultConfig() {
        return {
            objects: {
                'ObjectA': { min: 13.1, max: 13.5, name: 'ObjectA' },
                'ObjectB': { min: 15.5, max: 15.9, name: 'ObjectB' },
                'ObjectC': { min: 18.0, max: 18.4, name: 'ObjectC' }
            },
            filter_params: {
                bufferSize: 10,
                minSamples: 5,
                stableThreshold: 1.0
            }
        };
    }

    loadConfig(filePath = null) {
        const configFile = filePath || this.configPath;
        
        try {
            if (fs.existsSync(configFile)) {
                const data = fs.readFileSync(configFile, 'utf8');
                this.config = JSON.parse(data);
                return true;
            } else {
                console.log('Config file not found, using defaults');
                return false;
            }
        } catch (error) {
            console.error('Error loading config:', error);
            return false;
        }
    }

    saveConfig(filePath = null) {
        const configFile = filePath || this.configPath;
        
        try {
            fs.writeFileSync(configFile, JSON.stringify(this.config, null, 2));
            return true;
        } catch (error) {
            console.error('Error saving config:', error);
            return false;
        }
    }

    getObjects() {
        return this.config.objects;
    }

    getFilterParams() {
        return this.config.filter_params;
    }

    updateObject(objId, minDist, maxDist, name) {
        this.config.objects[objId] = {
            min: minDist,
            max: maxDist,
            name: name || objId
        };
    }

    updateFilterParams(params) {
        this.config.filter_params = { ...this.config.filter_params, ...params };
    }
}

module.exports = ConfigManager;
```

---

## 3. Max Patch 設計

### メインパッチ構成
```
[serial 115200] 
    ↓
[unpack $1 $2 $3 $4 $5]  // timestamp, status, ch1, ch2, ch3
    ↓
[route ch1 ch2 ch3]
    ↓
[node.script sensor_processor.js]
    ↓
[route filtered_ch1 filtered_ch2 filtered_ch3 identified_ch1 identified_ch2 identified_ch3]
    ↓
[print] [bang] [outlet] [send~] etc.
```

### 出力データ形式
#### フィルタリング結果
- `filtered_ch1 raw_value filtered_value stable_flag`
- 例: `filtered_ch1 13.45 13.43 1`

#### 識別結果  
- `identified_ch1 object_name confidence in_range_flag`
- 例: `identified_ch1 ObjectA 0.85 1`

### Max メッセージ例
```
// 設定読み込み
[load_config ./my_config.json(

// チャンネルデータ送信
[13.45( → [s ch1]
[15.67( → [s ch2] 
[18.23( → [s ch3]
```

---

## 4. 設定ファイル

### config.json
```json
{
  "objects": {
    "ObjectA": { 
      "min": 13.1, 
      "max": 13.5, 
      "name": "ObjectA" 
    },
    "ObjectB": { 
      "min": 15.5, 
      "max": 15.9, 
      "name": "ObjectB" 
    },
    "ObjectC": { 
      "min": 18.0, 
      "max": 18.4, 
      "name": "ObjectC" 
    }
  },
  "filter_params": {
    "bufferSize": 10,
    "minSamples": 5,
    "stableThreshold": 1.0
  }
}
```

---

## 5. 実装ステップ

### Phase 1: 基本フィルタリング機能 (1-2日)
1. `sensor_filter.js` の実装
2. 基本的な `sensor_processor.js` の作成
3. Max パッチでの動作テスト
4. フィルタリング精度の確認

**成果物:**
- 安定化されたセンサーデータの出力
- 生データとフィルタリングデータの比較確認

### Phase 2: オブジェクト識別機能 (1-2日)
1. `object_identifier.js` の実装
2. `sensor_processor.js` への識別機能統合
3. 識別精度のテスト
4. 信頼度計算の調整

**成果物:**
- オブジェクト識別結果の出力
- 信頼度スコアの評価

### Phase 3: 設定管理機能 (1日)
1. `config_manager.js` の実装
2. JSON設定ファイルの読み込み/保存
3. 動的設定更新機能
4. Max からの設定変更インターフェース

**成果物:**
- 設定ファイルによる柔軟な調整
- ランタイム設定変更機能

### Phase 4: Max統合とテスト (1-2日)
1. Max パッチの完成
2. 全機能の統合テスト
3. パフォーマンス最適化
4. エラーハンドリングの強化

**成果物:**
- 完全に動作するMax/MSPシステム
- ドキュメント整備

### Phase 5: 最適化と調整 (1日)
1. リアルタイム性能の最適化
2. メモリ使用量の最適化
3. パラメータの最終調整
4. 使用マニュアルの作成

**成果物:**
- 本番環境対応システム
- 完全なドキュメンテーション

---

## 6. 技術的考慮事項

### パフォーマンス
- Node.js の非同期処理を活用
- バッファサイズの最適化
- ガベージコレクション対策

### エラーハンドリング
- 不正データの処理
- 設定ファイルエラーの対応
- Max/MSP との通信エラー対応

### 拡張性
- オブジェクト数の動的変更
- フィルタリングアルゴリズムの交換可能性
- 新しいセンサーチャンネルの追加対応

### デバッグ
- コンソールログ出力
- Max コンソールでのデバッグ情報
- 設定変更の即座反映

---

## 7. 期待される効果

### 精度向上
- Pythonバージョンと同等以上の識別精度
- Max/MSP環境での最適化されたパフォーマンス

### 統合性
- Max/MSP エコシステムとの完全統合
- リアルタイム音響処理との連携可能性

### 保守性
- モジュラー設計による保守の容易さ
- 設定ファイルによる柔軟な調整

---

## 8. 必要なリソース

### 開発環境
- Max/MSP (Node for Max対応版)
- Node.js 環境
- VL53L0X ToF センサー
- 適切なハードウェア環境

### 開発期間
- 合計: 5-8日
- テスト・調整期間込み

### スキル要件
- JavaScript/Node.js プログラミング
- Max/MSP パッチング
- センサーデータ処理の理解
- リアルタイムシステム開発経験

---

この移植プランに従って実装することで、Python版と同等の機能を持つMax/MSP対応オブジェクト識別システムが構築できます。