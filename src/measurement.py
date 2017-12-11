#!/usr/bin/python
#--------------------------------------
import json
import datetime
#--------------------------------------
# Sensor class
#--------------------------------------
class Sensor:

  # Initialize and load calibration table
  def __init__(self, name, minimum, maximum, low_thr=None, hi_thr=None, low_msg=None,
               hi_msg=None, value=None, unit=""):
    self.name          = name
    self.value         = value
    self.unit          = unit
    self.min           = minimum
    self.max           = maximum
    self.low_thr       = low_thr
    self.hi_thr        = hi_thr

    self.alerts = {}

    if low_msg is not None:
      self.alerts[low_msg] = 'clear'
    if hi_msg is not None:
      self.alerts[hi_msg]  = 'clear'

    self.low_thr_msg   = low_msg
    self.hi_thr_msg    = hi_msg

  def __iter__(self):
    return self.__dict__.iteritems()

  def pub_json(self):
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%m:%S.%f')[0:-3] + 'Z'
    return { "name":self.name, "value":self.value, "recorded":timestamp }

  def is_valid(self, new_val):
    if new_val >= self.min and new_val <= self.max:
      self.value = new_val
    else:
      self.value = None

  def is_alert(self):
    self.alerts[self.low_thr_msg] = 'clear'
    self.alerts[self.hi_thr_msg]  = 'clear'

    if self.value is None:
      return None

    if self.low_thr != self.min and self.low_thr > self.min and \
      self.value < self.low_thr and self.low_thr_msg is not None:
      self.alerts[self.low_thr_msg] = 'set'
      return self.low_thr_msg

    if self.hi_thr != self.max and self.hi_thr < self.max and \
      self.value > self.hi_thr and self.hi_thr_msg is not None:
      self.alerts[self.hi_thr_msg] = 'set'
      return self.hi_thr_msg

    return None
