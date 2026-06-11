#include <Adafruit_NeoPixel.h>
#include <M5Unified.h>

#define PIN 26
#define NUMPIXELS 3

Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

void setup() {
  M5.begin();
  M5.Power.begin();
  pixels.begin();
  M5.Lcd.println(("RGB Example"));
}

void loop() {
  // pixels.sin8(n); n=0-255
  for (int i = 0; i < NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(0, 0, 100));
  }
  pixels.show();
}