#!/usr/bin/python
#--------------------------------------
import smbus
import time
from bme280 import BME280

#--------------------------------------
# CONSTANTS
#--------------------------------------
# Default device I2C address
I2C_ADC_DEVICE = 0x50

# I2C bus
bus = smbus.SMBus(1)

#--------------------------------------
# I2C-ADC specific functions
#--------------------------------------

def readADC(addr=I2C_ADC_DEVICE):
  
  REG_ADDR_RESULT = 0x00
  REG_ADDR_ALERT  = 0x01
  REG_ADDR_CONFIG = 0x02
  REG_ADDR_LIMITL = 0x03
  REG_ADDR_LIMITH = 0x04
  REG_ADDR_HYST   = 0x05
  REG_ADDR_CONVL  = 0x06
  REG_ADDR_CONVH  = 0x07

  bus.write_byte_data(addr, REG_ADDR_CONFIG, 0x20)

  data = bus.read_i2c_block_data(addr, REG_ADDR_RESULT, 2)
  raw_val = (data[0] & 0x0f) << 8 | data[1]
  return raw_val


def main():

  bme280 = BME280()
  chip_id, chip_version = bme280.read_version()
  print "BME280 Chip ID     :", chip_id
  print "BME280 Version     :", chip_version

  while(True):

    soil = readADC()
    temperature, pressure, humidity = bme280.read_all()

    print "Temperature : ", temperature, "C"
    print "Pressure    : ", pressure, "hPa"
    print "Humidity    : ", humidity, "%"
    print "Soil moist  : ", soil, "%"

    time.sleep(1)

if __name__=="__main__":
   main()
