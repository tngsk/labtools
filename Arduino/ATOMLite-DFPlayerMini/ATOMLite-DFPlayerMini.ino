#include "HardwareSerial.h"
#include "DFRobotDFPlayerMini.h"

#define RX 33 // Connects to module's RX 
#define TX 23 // Connects to module's TX 

HardwareSerial dfSD(1); // Use UART channel 1
DFRobotDFPlayerMini player;
   
void setup() {
  Serial.begin(115200);
  dfSD.begin(9600, SERIAL_8N1, RX, TX);
  
  Serial.println();
  Serial.println(F("DFRobot DFPlayer Mini Demo"));
  Serial.println(F("Initializing DFPlayer ... (May take 3~5 seconds)"));
  
  delay(5000);

  if (!player.begin(dfSD)) {
    Serial.println(F("Unable to begin:"));
    Serial.println(F("1.Please recheck the connection!"));
    Serial.println(F("2.Please insert the SD card!"));
    while(true){
      delay(0); // Code to compatible with ESP8266 watch dog.
    }
  }
  Serial.println(F("DFPlayer Mini online."));

  if (player.begin(dfSD)) {
    Serial.println("OK");
    player.volume(25); //0~30で音量指定
  }
  
  else {
    Serial.println("Connecting to DFPlayer Mini failed!");
  }
}

void loop() {
  Serial.println("Playing #1");
  player.play(1);
  Serial.println("play start");
  delay(5000);
  Serial.println("played");
  delay(1000);

  Serial.println("Playing #2");
  player.play(2);
  Serial.println("play start");
  delay(10000);
  Serial.println("played");
  delay(1000);
}