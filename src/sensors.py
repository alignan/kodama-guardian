#!/usr/bin/python
#--------------------------------------
import smbus
import time
from bme280 import BME280
from soil import SoilMoist

def main():

  bme280 = BME280()
  soil_hum = SoilMoist()

  chip_id, chip_version = bme280.read_version()
  print "BME280 Chip ID     :", chip_id
  print "BME280 Version     :", chip_version

  while(True):

    soil = soil_hum.read_raw()
    temperature, pressure, humidity = bme280.read_all()

    print "Temperature : ", temperature, "C"
    print "Pressure    : ", pressure, "hPa"
    print "Humidity    : ", humidity, "%"
    print "Soil moist  : ", soil, "%"

    time.sleep(1)

if __name__=="__main__":
   main()
