#include <M5Unified.h>
#include <ArduinoOSCWiFi.h>
#include <Adafruit_NeoPixel.h>

// for WiFi Network
const char *ssid = "ngsk-lab";
const char *password = "cdxd2017";
const IPAddress gateway(10, 37, 15, 254);
const IPAddress subnet(255, 255, 255, 0);

// OSC
const char* host = "10.37.15.2";
const int send_port = 9000;
const int recv_port = 9001;

// LED
#define PIN 26
#define NUMPIXELS 60

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);
#define DELAYVAL 5

int clrR = 0, clrG = 150, clrB = 0;

void setup() {
  M5.begin();
  pixels.begin();
  pixels.clear();
  Serial.begin(115200);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500);
  }
  WiFi.config(WiFi.localIP(), gateway, subnet);
  Serial.println(WiFi.localIP());
  OscWiFi.subscribe(recv_port, "/Color", clrR, clrG, clrB);
}

void loop() {
  M5.update();
  if (M5.BtnA.isPressed()) {
    Serial.println(WiFi.localIP());
  }
  
  for(int i=0; i<NUMPIXELS; i++) {
    pixels.setPixelColor(i, pixels.Color(clrR, clrG, clrB));
  }
  pixels.show();
  OscWiFi.update();

}