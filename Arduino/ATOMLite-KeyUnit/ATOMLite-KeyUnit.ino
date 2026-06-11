#include <FastLED.h>
#include <M5Unified.h>

#define KEY_PIN  32
#define LED_PIN 26

CRGB LED[1];

void setup() {
    M5.begin();
    Serial.begin(115200);
    pinMode(KEY_PIN, INPUT_PULLUP);
    FastLED.addLeds<SK6812, LED_PIN, GRB>(LED, 1);
    LED[0] = CRGB::Blue;
    FastLED.setBrightness(0);
}

void loop() {
    if (!digitalRead(KEY_PIN)) {
        FastLED.setBrightness(255);
        FastLED.show();
        Serial.println(1);
        while (!digitalRead(KEY_PIN))
          Serial.println(1);
            ;
    } else {
        FastLED.setBrightness(0);
        FastLED.show();
        Serial.println(0);
    }
    delay(100);
}