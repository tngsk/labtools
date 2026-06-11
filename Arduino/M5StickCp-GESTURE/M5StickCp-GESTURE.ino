#include <M5Unified.h>
#include <DFRobot_PAJ7620U2.h>

DFRobot_PAJ7620U2 sensor;

void setup() {
    M5.begin();
    Serial.begin(115200);
    delay(300);
    Serial.println("PAJ7620U2 Init");
    while (sensor.begin() != 0) {
        Serial.println("initial PAJ7620U2 failure!");
        delay(500);
    }
    sensor.setGestureHighRate(true);
    Serial.println("Start to recognize");
}

void loop() {
    /*
     * eGestureNone  eGestureRight  eGestureLeft  eGestureUp  eGestureDown
     * eGestureForward eGestureBackward  eGestureClockwise eGestureAntiClockwise
     * eGestureWave  eGestureWaveSlowlyDisorder eGestureWaveSlowlyLeftRight
     * eGestureWaveSlowlyUpDown  eGestureWaveSlowlyForwardBackward
     */
    DFRobot_PAJ7620U2::eGesture_t gesture = sensor.getGesture();
    if (gesture != sensor.eGestureNone) {
        /*
         * "None","Right","Left", "Up", "Down", "Forward", "Backward",
         * "Clockwise", "Anti-Clockwise", "Wave", "WaveSlowlyDisorder",
         * "WaveSlowlyLeftRight", "WaveSlowlyUpDown",
         * "WaveSlowlyForwardBackward"
         */
        String description = sensor.gestureDescription(gesture);
        Serial.println("Gesture = " + description);
    }
}