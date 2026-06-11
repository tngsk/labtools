#include "M5Unified.h"
#include <Wire.h>
#include "Adafruit_VL53L0X.h"

// TCA9546A I2Cハブのアドレス
#define TCA9546A_ADDR 0x70

// 測定値フィルタリング設定
#define MIN_VALID_DISTANCE 5     // 最小有効距離 (mm)
#define MAX_VALID_DISTANCE 1000   // 最大有効距離 (mm)

// センサー読み取り結果の構造体
struct SensorReading {
  uint16_t distance_mm;
  uint8_t range_status;
  uint16_t signal_rate;
  uint16_t ambient_rate;
  bool valid;
  uint32_t measurement_time_us;
  bool filtered_out;  // 異常値として除外されたかどうか
};

// 直前の有効値を保持
uint16_t lastValidDistance[3] = {MAX_VALID_DISTANCE, MAX_VALID_DISTANCE, MAX_VALID_DISTANCE};

// VL53L0Xオブジェクト
Adafruit_VL53L0X lox = Adafruit_VL53L0X();

// チャンネル情報
const int CHANNEL_COUNT = 3;
bool channelActive[CHANNEL_COUNT] = {false, false, false};
String channelNames[CHANNEL_COUNT] = {"ch1", "ch2", "ch3"};

// 測定設定 - 高精度重視
const unsigned long MEASUREMENT_INTERVAL = 50; // 50ms間隔 - 20Hz
const uint32_t TIMING_BUDGET = 100000; // 100ms - 高精度設定

// 統計用カウンタ
unsigned long measurementCount = 0;
unsigned long startTime = 0;

// 出力設定
bool jsonFormat = false;
bool includeMetadata = true;

void setup() {
  M5.begin();
  Serial.begin(115200); // 高速通信
  delay(1000);

  startTime = millis();

  Serial.println("{\"type\":\"system\",\"message\":\"ATOM Lite VL53L0X High-Precision Data Logger\",\"version\":\"3.0\"}");
  Serial.println("{\"type\":\"system\",\"message\":\"Initializing I2C...\"}");

  // I2C初期化 - 高速設定
  Wire.begin(26, 32); // ATOM LiteのSDA=26, SCL=32
  Wire.setClock(400000); // 400kHz - 高速モード
  delay(100);

  // TCA9546A検出
  if (!detectTCA9546A()) {
    Serial.println("{\"type\":\"error\",\"message\":\"TCA9546A not found\",\"fatal\":true}");
    return;
  }

  // センサー初期化
  initializeSensors();

  // アクティブセンサー数を報告
  int activeCount = 0;
  for (int i = 0; i < CHANNEL_COUNT; i++) {
    if (channelActive[i]) activeCount++;
  }

  Serial.printf("{\"type\":\"system\",\"message\":\"Initialization complete\",\"active_sensors\":%d,\"sample_rate_hz\":%.1f}\n",
                activeCount, 1000.0 / MEASUREMENT_INTERVAL);
  Serial.println("{\"type\":\"system\",\"message\":\"Starting measurement...\"}");

  // データヘッダー出力
  if (includeMetadata) {
    Serial.println("{\"type\":\"metadata\",\"channels\":[\"ch1\",\"ch2\",\"ch3\"],\"units\":\"mm\",\"timing_budget_us\":" + String(TIMING_BUDGET) + "}");
  }

  delay(100);
}

bool detectTCA9546A() {
  Wire.beginTransmission(TCA9546A_ADDR);
  byte error = Wire.endTransmission();

  if (error == 0) {
    Serial.printf("{\"type\":\"system\",\"message\":\"TCA9546A detected\",\"address\":\"0x%02X\"}\n", TCA9546A_ADDR);
    return true;
  } else {
    Serial.printf("{\"type\":\"error\",\"message\":\"TCA9546A not found\",\"address\":\"0x%02X\",\"error_code\":%d}\n", TCA9546A_ADDR, error);
    return false;
  }
}

void selectChannel(uint8_t channel) {
  if (channel >= CHANNEL_COUNT) return;

  Wire.beginTransmission(TCA9546A_ADDR);
  Wire.write(1 << channel);
  Wire.endTransmission();
  delayMicroseconds(500); // 最小限の安定化時間
}

void disableAllChannels() {
  Wire.beginTransmission(TCA9546A_ADDR);
  Wire.write(0x00);
  Wire.endTransmission();
}

void initializeSensors() {
  Serial.println("{\"type\":\"system\",\"message\":\"Initializing sensors...\"}");

  for (int channel = 0; channel < CHANNEL_COUNT; channel++) {
    selectChannel(channel);
    delay(10);

    if (lox.begin()) {
      // 高精度設定
      lox.configSensor(Adafruit_VL53L0X::VL53L0X_SENSE_HIGH_ACCURACY);

      // タイミングバジェット設定
      if (lox.setMeasurementTimingBudgetMicroSeconds(TIMING_BUDGET)) {
        channelActive[channel] = true;
        Serial.printf("{\"type\":\"system\",\"message\":\"Channel %d (%s) initialized\",\"channel\":%d,\"name\":\"%s\"}\n",
                      channel, channelNames[channel].c_str(), channel, channelNames[channel].c_str());
      } else {
        channelActive[channel] = false;
        Serial.printf("{\"type\":\"error\",\"message\":\"Channel %d timing budget failed\",\"channel\":%d}\n", channel, channel);
      }
    } else {
      channelActive[channel] = false;
      Serial.printf("{\"type\":\"error\",\"message\":\"Channel %d initialization failed\",\"channel\":%d}\n", channel, channel);
    }

    delay(50);
  }

  disableAllChannels();
}



uint16_t getOutputValue(uint8_t channel, uint16_t distance, uint8_t range_status) {
  // Range Status 4 (Phase failures) の場合は0を返す
  if (range_status == 4) {
    return 0;
  }

  // 有効範囲外の値の場合は直前の有効値を返す
  if (distance < MIN_VALID_DISTANCE || distance > MAX_VALID_DISTANCE) {
    return lastValidDistance[channel];
  }

  // 有効値の場合は保存して返す
  if (channel < CHANNEL_COUNT) {
    lastValidDistance[channel] = distance;
  }
  return distance;
}

SensorReading readChannelWithMetadata(uint8_t channel) {
  SensorReading reading = {0, 255, 0, 0, false, 0, false};

  if (channel >= CHANNEL_COUNT || !channelActive[channel]) {
    reading.filtered_out = true;
    return reading;
  }

  selectChannel(channel);
  delayMicroseconds(500);

  uint32_t startTime = micros();
  VL53L0X_RangingMeasurementData_t measure;
  lox.rangingTest(&measure, false);
  uint32_t endTime = micros();

  reading.measurement_time_us = endTime - startTime;
  reading.distance_mm = measure.RangeMilliMeter;
  reading.range_status = measure.RangeStatus;
  reading.signal_rate = measure.SignalRateRtnMegaCps;
  reading.ambient_rate = measure.AmbientRateRtnMegaCps;

  // 出力値を決定（有効性チェック含む）
  uint16_t outputValue = getOutputValue(channel, reading.distance_mm, reading.range_status);
  reading.distance_mm = outputValue;

  // 有効性判定
  reading.valid = (reading.range_status != 4 &&
                   reading.distance_mm >= MIN_VALID_DISTANCE &&
                   reading.distance_mm <= MAX_VALID_DISTANCE);
  reading.filtered_out = false;

  return reading;
}

void outputMeasurement() {
  uint32_t timestamp = millis();
  measurementCount++;

  if (jsonFormat) {
    // JSON形式での詳細出力
    Serial.printf("{\"type\":\"measurement\",\"timestamp\":%lu,\"sequence\":%lu,\"channels\":[",
                  timestamp, measurementCount);

    for (int i = 0; i < CHANNEL_COUNT; i++) {
      if (i > 0) Serial.print(",");

      if (!channelActive[i]) {
        Serial.print("null");
        continue;
      }

      SensorReading reading = readChannelWithMetadata(i);

      Serial.print("{");
      Serial.printf("\"name\":\"%s\",", channelNames[i].c_str());

      Serial.printf("\"distance\":%d,", reading.distance_mm);
      Serial.printf("\"status\":%d,", reading.range_status);
      Serial.printf("\"valid\":%s,", reading.valid ? "true" : "false");

      if (includeMetadata) {
        Serial.printf("\"signal_rate\":%d,", reading.signal_rate);
        Serial.printf("\"ambient_rate\":%d,", reading.ambient_rate);
        Serial.printf("\"measurement_time_us\":%lu", reading.measurement_time_us);
      } else {
        // メタデータなしの場合は末尾のカンマを削除
        Serial.print("\"measurement_time_us\":" + String(reading.measurement_time_us));
      }

      Serial.print("}");
    }

    Serial.println("]}");
  } else {
    // CSV形式での高速出力
    Serial.printf("%lu,%lu", timestamp, measurementCount);

    for (int i = 0; i < CHANNEL_COUNT; i++) {
      Serial.print(",");

      if (!channelActive[i]) {
        Serial.print("N/A");
        continue;
      }

      SensorReading reading = readChannelWithMetadata(i);

      Serial.print(reading.distance_mm);
    }

    Serial.println();
  }

  disableAllChannels();
}

void handleSerialCommands() {
  if (!Serial.available()) return;

  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command == "json") {
    jsonFormat = true;
    Serial.println("{\"type\":\"system\",\"message\":\"Output format: JSON\"}");
  } else if (command == "csv") {
    jsonFormat = false;
    Serial.println("# Output format: CSV");
    Serial.println("# timestamp,sequence,ch1,ch2,ch3");
  } else if (command == "meta_on") {
    includeMetadata = true;
    Serial.println("{\"type\":\"system\",\"message\":\"Metadata enabled\"}");
  } else if (command == "meta_off") {
    includeMetadata = false;
    Serial.println("{\"type\":\"system\",\"message\":\"Metadata disabled\"}");
  } else if (command == "status") {
    outputSystemStatus();
  } else if (command == "reset") {
    Serial.println("{\"type\":\"system\",\"message\":\"Resetting...\"}");
    ESP.restart();
  } else {
    Serial.printf("{\"type\":\"error\",\"message\":\"Unknown command: %s\"}\n", command.c_str());
  }
}

void outputSystemStatus() {
  uint32_t uptime = millis() - startTime;
  float sampleRate = (measurementCount * 1000.0) / uptime;

  Serial.print("{\"type\":\"status\",");
  Serial.printf("\"uptime_ms\":%lu,", uptime);
  Serial.printf("\"measurement_count\":%lu,", measurementCount);
  Serial.printf("\"actual_sample_rate_hz\":%.2f,", sampleRate);
  Serial.printf("\"free_ram\":%d,", ESP.getFreeHeap());
  Serial.print("\"channels\":[");

  for (int i = 0; i < CHANNEL_COUNT; i++) {
    if (i > 0) Serial.print(",");
    Serial.print("{");
    Serial.printf("\"id\":%d,", i);
    Serial.printf("\"name\":\"%s\",", channelNames[i].c_str());
    Serial.printf("\"active\":%s", channelActive[i] ? "true" : "false");
    Serial.print("}");
  }

  Serial.println("]}");
}

void loop() {
  M5.update();

  // シリアルコマンド処理
  handleSerialCommands();

  // 高速測定ループ
  static unsigned long lastMeasurement = 0;
  unsigned long currentTime = millis();

  if (currentTime - lastMeasurement >= MEASUREMENT_INTERVAL) {
    outputMeasurement();
    lastMeasurement = currentTime;
  }

  // ボタンA: フォーマット切り替え
  if (M5.BtnA.wasPressed()) {
    jsonFormat = !jsonFormat;
    if (jsonFormat) {
      Serial.println("{\"type\":\"system\",\"message\":\"Switched to JSON format\"}");
    } else {
      Serial.println("# Switched to CSV format");
      Serial.println("# timestamp,sequence,ch1,ch2,ch3");
    }
    delay(200);
  }

  yield(); // WDTリセット
}
