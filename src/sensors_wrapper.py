#!/usr/bin/python
# coding=utf-8
#--------------------------------------------------------------------
import os
import sys
import json
import yaml
import inspect
import datetime
import importlib

#--------------------------------------------------------------------
# Sensors class: imports from a YAML file and creates Sensor objects
#--------------------------------------------------------------------
class Sensors:
  def __init__(self, file_path):
    self.my_sensors = list()
    with open(os.path.join(sys.path[0], file_path), 'r') as f:
      measurements = yaml.load(f)
      for key, value in measurements.iteritems():
        my_mod = None
        try:
          my_mod = importlib.import_module(value["source"])
          my_class = getattr(my_mod, value["class"])
          my_sensor = my_class()
        except ImportError:
          raise SystemExit("Failed to load {0}".format(value["source"]))

        a = Sensor(name=key, minimum=value["minimum"], maximum=value["maximum"],
                   low_thr=(value["low_thr"] if "low_thr" in value else None),
                   hi_thr=(value["hi_thr"] if "hi_thr" in value else None),
                   low_msg=(value["low_msg"] if "low_msg" in value else None),
                   hi_msg=(value["hi_msg"] if "hi_msg" in value else None),
                   unit=value["unit"], obj=my_sensor, cmd=value["command"])
        self.my_sensors.append(a)

    # keep track of ongoing alerts
    self.ongoing_alerts = list()
    for sensor in self.my_sensors:
      a = {}
      if sensor.value.low_thr_msg
      self.ongoing_alerts[sensor.name] = 

  def read_sensors(self):
    for sensor in self.my_sensors:
      try:
        func = getattr(sensor.obj, sensor.cmd)
        new_val = func()
        sensor.is_valid(new_val)
      except AttributeError:
        raise SystemExit("failed: method {0} not found in {1}".format(sensor.cmd, sensor.obj))

  def read_sensor(self, a_sensor):
    pass

  def check_alarms(self):
    a = list()
    for sensor in self.sensor:
      an_alert = sensor.is_alert()
      if an_alert is not None and sensor.



  alerts_list = []
  # check first specific sensor alerts
  for key, sensor in MQTT_MEASUREMENT_MAP['measurements'].iteritems():
    an_alert = sensor.is_alert()
    # if the recorded alert is different than the new alert, publish
    if an_alert is not None and MQTT_ALERTS_MAP['alerts'][an_alert] != sensor.alerts[an_alert]:
      MQTT_ALERTS_MAP['alerts'][an_alert] = sensor.alerts[an_alert]
      print "!!!! {0} @ {1} : {2}{3}".format(an_alert, sensor.name, sensor.value, sensor.unit)
      alerts_list.append('{"name":{0}, "state":{1}}'.format(an_alert, MQTT_ALERTS_MAP['alerts'][an_alert]))



  def __str__( self ):
    a = ''
    for sensor in self.my_sensors:
      a = a + sensor.name + ': ' + str(sensor.value) + sensor.unit + ', '
    return a[:-2].encode('utf-8')

#--------------------------------------------------------------------
# Sensor class
#--------------------------------------------------------------------
class Sensor:
  # Initialize and load calibration table
  def __init__(self, name, obj, cmd, unit, minimum, maximum, low_thr=None,
               hi_thr=None, low_msg=None, hi_msg=None, value=None):
    self.name          = name
    self.value         = value
    self.unit          = unit
    self.min           = minimum
    self.max           = maximum
    self.low_thr       = low_thr
    self.hi_thr        = hi_thr
    self.cmd           = cmd.replace('\r', '')
    self.obj           = obj

    self.alerts = dict()

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

  def read_sensor(self):
    f = StringFunction(self.cmd)
    self.value = f()
    return self.value

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
