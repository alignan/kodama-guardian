#!/usr/bin/python
#--------------------------------------
import os
import time

# I2C address
I2C_DEVICE  = 0x50

# I2C bus
is_raspberry = 1
if os.uname()[4][:3] == 'arm':
  import smbus
  bus = smbus.SMBus(1)
else:
  is_raspberry = 0

#--------------------------------------
# ADC to I2C sensor class (soil)
#--------------------------------------
class SoilMoist:
  def __init__(self, addr=I2C_DEVICE):
    self.addr = addr
    self.REG_ADDR_RESULT = 0x00
    self.REG_ADDR_ALERT  = 0x01
    self.REG_ADDR_CONFIG = 0x02
    self.REG_ADDR_LIMITL = 0x03
    self.REG_ADDR_LIMITH = 0x04
    self.REG_ADDR_HYST   = 0x05
    self.REG_ADDR_CONVL  = 0x06
    self.REG_ADDR_CONVH  = 0x07

  def read_raw(self):
    if is_raspberry:
      bus.write_byte_data(self.addr, self.REG_ADDR_CONFIG, 0x20)
      data = bus.read_i2c_block_data(self.addr, self.REG_ADDR_RESULT, 2)
      raw_val = (data[0] & 0x0f) << 8 | data[1]
      return raw_val
    else:
      return 1000
