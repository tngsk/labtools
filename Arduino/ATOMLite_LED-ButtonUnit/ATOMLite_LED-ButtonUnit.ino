#include <Adafruit_NeoPixel.h>
#include <M5Unified.h>

#define RGB_LED_PIN 26
#define NUMPIXELS 3
Adafruit_NeoPixel pixels = Adafruit_NeoPixel(NUMPIXELS, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);

#define BUTTON_UNIT_PIN 32

int r = 0;
int g = 0;
int b = 0;

void setup() {
  M5.begin();
  Serial.begin(115200);

  M5.Power.begin();
  pixels.begin();

  pinMode(BUTTON_UNIT_PIN, INPUT);
}

void loop() {
  int button_value = digitalRead(BUTTON_UNIT_PIN);
  // Serial.println(button_value);
  if (button_value == 0) {
    r = (r + 1) % 255;
    g = (g + 2) % 255;
    b = (b + 3) % 255;
    for (int i = 0; i < NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(r, g, b));
    }
  } else {
    for (int i = 0; i < NUMPIXELS; i++) {
      pixels.setPixelColor(i, pixels.Color(0, 0, 0));
    }
  }
  pixels.show();
}