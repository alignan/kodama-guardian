#!/usr/bin/python
#--------------------------------------
import os
import time
from ctypes import c_short
from ctypes import c_byte
from ctypes import c_ubyte

# I2C address
BME280_DEVICE  = 0x77

# I2C bus
is_raspberry = 1
if os.uname()[4][:3] == 'arm':
  import smbus
  bus = smbus.SMBus(1)
else:
  is_raspberry = 0

#--------------------------------------
# AUX FUNCTIONS
#--------------------------------------
def getShort(data, index):
  # return two bytes from data as a signed 16-bit value
  return c_short((data[index+1] << 8) + data[index]).value

def getUShort(data, index):
  # return two bytes from data as an unsigned 16-bit value
  return (data[index+1] << 8) + data[index]

def getChar(data,index):
  # return one byte from data as a signed char
  result = data[index]
  if result > 127:
    result -= 256
  return result

def getUChar(data,index):
  # return one byte from data as an unsigned char
  result =  data[index] & 0xFF
  return result

#--------------------------------------
# BME280 class
#--------------------------------------
class BME280:

  REG_DATA  = 0xF7
  T_FINE    = 0

  # Initialize and load calibration table
  def __init__(self, addr=BME280_DEVICE):
    global T_FINE
    self.addr = addr
    self.REG_ID          = 0xD0
    self.REG_CONTROL     = 0xF4
    self.REG_CONFIG      = 0xF5
    self.REG_CONTROL_HUM = 0xF2
    self.REG_HUM_MSB     = 0xFD
    self.REG_HUM_LSB     = 0xFE

    self.MODE            = 1
    self.OVERSAMPLE_TEMP = 2
    self.OVERSAMPLE_PRES = 2
    self.OVERSAMPLE_HUM  = 2

    # Sampling configuration
    if is_raspberry:
      bus.write_byte_data(self.addr, self.REG_CONTROL_HUM, self.OVERSAMPLE_HUM)
      control = self.OVERSAMPLE_TEMP << 5 | self.OVERSAMPLE_PRES << 2 | self.MODE
      bus.write_byte_data(self.addr, self.REG_CONTROL, control)

      # Calibration table
      self.cal1 = bus.read_i2c_block_data(self.addr, 0x88, 24)
      self.cal2 = bus.read_i2c_block_data(self.addr, 0xA1, 1)
      self.cal3 = bus.read_i2c_block_data(self.addr, 0xE1, 7)
    else:
      self.cal1 = 1
      self.cal2 = 1
      self.cal3 = 1

    # Convert byte data to word values
    self.dig_T1 = getUShort(self.cal1, 0)
    self.dig_T2 = getShort(self.cal1, 2)
    self.dig_T3 = getShort(self.cal1, 4)

    self.dig_P1 = getUShort(self.cal1, 6)
    self.dig_P2 = getShort(self.cal1, 8)
    self.dig_P3 = getShort(self.cal1, 10)
    self.dig_P4 = getShort(self.cal1, 12)
    self.dig_P5 = getShort(self.cal1, 14)
    self.dig_P6 = getShort(self.cal1, 16)
    self.dig_P7 = getShort(self.cal1, 18)
    self.dig_P8 = getShort(self.cal1, 20)
    self.dig_P9 = getShort(self.cal1, 22)

    self.dig_H1 = getUChar(self.cal2, 0)
    self.dig_H2 = getShort(self.cal3, 0)
    self.dig_H3 = getUChar(self.cal3, 2)

    self.dig_H4 = getChar(self.cal3, 3)
    self.dig_H4 = (self.dig_H4 << 24) >> 20
    self.dig_H4 = self.dig_H4 | (getChar(self.cal3, 4) & 0x0F)

    self.dig_H5 = getChar(self.cal3, 5)
    self.dig_H5 = (self.dig_H5 << 24) >> 20
    self.dig_H5 = self.dig_H5 | (getUChar(self.cal3, 4) >> 4 & 0x0F)

    self.dig_H6 = getChar(self.cal3, 6)

    # Wait in ms (Datasheet Appendix B: Measurement time and current calculation)
    self.wait_time = 1.25 + (2.3 * self.OVERSAMPLE_TEMP) + ((2.3 * self.OVERSAMPLE_PRES) + 0.575) + \
                     ((2.3 * self.OVERSAMPLE_HUM) + 0.575)
    time.sleep(self.wait_time / 1000)

    # read temperature to load T_FINE
    read_temperature()

  def read_version(self):
    if is_raspberry:
      (self.chip_id, self.chip_version) = bus.read_i2c_block_data(self.addr, self.REG_ID, 2)
      return (self.chip_id, self.chip_version)
    else:
      return (96, 96)

  def read_temperature(self):
    global T_FINE
    if is_raspberry:
      data = bus.read_i2c_block_data(self.addr, self.REG_DATA, 8)
      temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)  

      var1 = ((((temp_raw >> 3) - (self.dig_T1 << 1))) * (self.dig_T2)) >> 11
      var2 = (((((temp_raw >> 4) - (self.dig_T1)) * ((temp_raw >> 4) - (self.dig_T1))) >> 12) * \
             (self.dig_T3)) >> 14
      T_FINE = var1 + var2
      temperature = float(((T_FINE * 5) + 128) >> 8)
      return (temperature / 100.0)
    else:
      return 25.5

  def read_pressure(self):
    if is_raspberry:
      data = bus.read_i2c_block_data(self.addr, self.REG_DATA, 8)
      pres_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)

      var1 = T_FINE / 2.0 - 64000.0
      var2 = var1 * var1 * self.dig_P6 / 32768.0
      var2 = var2 + var1 * self.dig_P5 * 2.0
      var2 = var2 / 4.0 + self.dig_P4 * 65536.0
      var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
      var1 = (1.0 + var1 / 32768.0) * self.dig_P1
      if var1 == 0:
        pressure = 0
      else:
        pressure = 1048576.0 - pres_raw
        pressure = ((pressure - var2 / 4096.0) * 6250.0) / var1
        var1 = self.dig_P9 * pressure * pressure / 2147483648.0
        var2 = pressure * self.dig_P8 / 32768.0
        pressure = pressure + (var1 + var2 + self.dig_P7) / 16.0
      return (pressure / 100.0)
    else:
      return 1000.0

  def read_humidity(self):
    if is_raspberry:
      data = bus.read_i2c_block_data(self.addr, self.REG_DATA, 8)
      hum_raw  = (data[6] << 8)  | data[7]

      humidity = T_FINE - 76800.0
      humidity = (hum_raw - (self.dig_H4 * 64.0 + self.dig_H5 / 16384.0 * humidity)) * \
                 (self.dig_H2 / 65536.0 * (1.0 + self.dig_H6 / 67108864.0 * humidity * \
                 (1.0 + self.dig_H3 / 67108864.0 * humidity)))
      humidity = humidity * (1.0 - self.dig_H1 * humidity / 524288.0)
      if humidity > 100:
        humidity = 100
      elif humidity < 0:
        humidity = 0
      return humidity
    else:
      return 50

  def read_all(self):
    temperature = read_temperature()
    pressure = read_pressure()
    humidity = read_humidity()
    return (temperature, pressure, humidity)
