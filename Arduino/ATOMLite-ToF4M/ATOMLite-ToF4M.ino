#include "M5Unified.h"
#include <Wire.h>
#include <VL53L1X.h>

VL53L1X sensor;

void setup() {
  M5.begin();
  Serial.begin(115200);
  M5.Ex_I2C.begin();
  sensor.setBus(&Wire);
  sensor.setTimeout(500);
  if (!sensor.init()) {
    Serial.println("Failed to detect and initialize sensor.");
    while (1)
      ;
  }
  // Use long distance mode and allow up to 50000 us (50 ms) for a
  // measurement. You can change these settings to adjust the performance of
  // the sensor, but the minimum timing budget is 20 ms for short distance
  // mode and 33 ms for medium and long distance modes. See the VL53L1X
  // datasheet for more information on range and timing limits.
  sensor.setDistanceMode(VL53L1X::Long);
  sensor.setMeasurementTimingBudget(50000);

  // Start continuous readings at a rate of one measurement every 50 ms (the
  // inter-measurement period). This period should be at least as long as the
  // timing budget.
  sensor.startContinuous(50);

  Serial.println("Done.");
}

void loop() {
  // Serial.print(sensor.read());
  // if (sensor.timeoutOccurred()) {
  //   Serial.print(" TIMEOUT");
  // }

  // Serial.println();

  M5.update();
  if (M5.BtnA.isPressed()) {
    Serial.println("A");
  }

  sensor.read();

  int status = sensor.ranging_data.range_status;
  int range_mm = sensor.ranging_data.range_mm;

  if (status == VL53L1X::RangeValid) {
    Serial.println(range_mm);
  }
  
  // Serial.print("range: ");
  // Serial.print(sensor.ranging_data.range_mm);
  // Serial.print("\tstatus: ");
  // Serial.print(
  //   VL53L1X::rangeStatusToString(sensor.ranging_data.range_status));
  // Serial.print("\tpeak signal: ");
  // Serial.print(sensor.ranging_data.peak_signal_count_rate_MCPS);
  // Serial.print("\tambient: ");
  // Serial.print(sensor.ranging_data.ambient_count_rate_MCPS);
}
