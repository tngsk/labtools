#include <M5Unified.h>
#include <Adafruit_NeoPixel.h>

// LED
#define PIN 26
#define NUMPIXELS 60
Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);


// LEDの色はとりあえず固定でRGBで決めます
int clrR = 0;
int clrG = 0;
int clrB = 150;

#define DELAYVAL 50  // アニメーションの速度調整用

int currentLed = 0;                // 現在点灯しているLEDの位置
unsigned long previousMillis = 0;  // 前回のLED更新時刻

void setup() {
  M5.begin();
  pixels.begin();
  pixels.clear();
}

void loop() {
  M5.update();
  if (M5.BtnA.isPressed()) {
    currentLed = 0;
  }

  unsigned long currentMillis = millis();

  // DELAYVAL間隔で次のLEDを点灯
  if (currentLed < NUMPIXELS) {
    if (currentMillis - previousMillis >= DELAYVAL) {
      previousMillis = currentMillis;

      // すべてのLEDを消灯
      pixels.clear();

      // 現在のLEDを点灯
      pixels.setPixelColor(currentLed, pixels.Color(clrR, clrG, clrB));
      // 前後のLEDも徐々に暗く点灯（テール効果）
      for (int i = 1; i < 10; i++) {
        int pos = (currentLed - i + NUMPIXELS) % NUMPIXELS;
        int brightness = 255 >> i;  // だんだん暗くなる
        pixels.setPixelColor(pos, pixels.Color(
                                    clrR * brightness / 255,
                                    clrG * brightness / 255,
                                    clrB * brightness / 255));
      }

      pixels.show();

      // 次のLEDへ移動
      currentLed = (currentLed + 1);
    }
  } else {
    // すべてのLEDを消灯
      pixels.clear();
  }
}