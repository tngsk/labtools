#include <M5StickCPlus.h>
#include "BluetoothSerial.h"

BluetoothSerial bts;

void setup() {
  M5.begin();
  M5.IMU.Init();
  // 画面の向きを回転する
  M5.Lcd.setRotation(3);
  //  Bluetoothを開始する
  bts.begin("M5StickC");
  //シリアル通信を開始する
  Serial.begin(115200);
}

void loop() {
  // センサー取得のための変数
  float ax;
  float ay;
  float az;
  // センサー値を文字に変換するための変数
  char axx[7];
  char ayy[7];
  char azz[7];
  char buf[32];

  M5.update();
  // 加速度センサー値を取得する
  M5.IMU.getAccelData(&ax, &ay, &az);
  
  // センサー値を文字列に変換する
  dtostrf(ax, 5, 2, axx);
  dtostrf(ay, 5, 2, ayy);
  dtostrf(az, 5, 2, azz);

  // "x y z"のフォーマットに加工する（スペース区切り）
  sprintf(buf, "%s %s %s", axx, ayy, axx);

  // "x,y,z"のフォーマットに加工する（カンマ区切り）
  // sprintf(buf, "%s,%s,%s", axx, ayy, axx);

  // M5Stickの画面をクリアする
  M5.Lcd.fillScreen(BLACK);
  // センサー値を画面に表示する
  M5.Lcd.drawString(buf, 10, 10, 4); 

  // センサー値をシリアル通信で送信する
  bts.println(buf);
  // センサー値をBTで送信する
  Serial.println(buf);

  // 待機
  delay(20);
}