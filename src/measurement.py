#!/usr/bin/python
#--------------------------------------
import json
import datetime
#--------------------------------------
# Sensor class
#--------------------------------------
class Sensor:

  # Initialize and load calibration table
  def __init__(self, name, minimum, maximum, low_thr, hi_thr, value=None, unit=""):
  	self.name    = name
  	self.value   = value
  	self.unit    = unit
  	self.min     = minimum
  	self.max     = maximum
  	self.low_thr = low_thr
  	self.hi_thr  = hi_thr

  def __iter__(self):
    return self.__dict__.iteritems()

  def pub_json(self):
    timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%m:%S.%f')[0:-3] + 'Z'
    return { "name":self.name, "value":self.value, "recorded":timestamp }

  def is_valid(self, new_val):
  	if new_val >= self.min and new_val <= self.max:
  	  self.value = new_val
  	self.value = None

  def is_alarm(self):
  	if self.value is None:
  	  return None
  	if self.low_thr != self.min and self.low_thr > self.min and self.value < self.low_thr:
  	  return "low_alarm"
  	if self.hi_thr != self.max and self.hi_thr < self.max and self.value > self.hi_thr:
  	  return "high_alarm"
  	return None
