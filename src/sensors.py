#!/usr/bin/python
# -*- coding: utf-8 -*-
#--------------------------------------
import os
import sys
import json
import gevent
import signal
import time
import threading

from copy import deepcopy

from measurement import Sensor
from bme280 import BME280
from soil import SoilMoist

import paho.mqtt.client as paho

CLOUD_HOST = "cloud-mqtt.relayr.io"
CLOUD_CERT = "/usr/src/app/src/cacert.pem"
CLOUD_PORT = 8883

# Values set in resin.io ENV VARS
PERIOD_MEAS   = int(os.getenv('PER_MEAS', 30000))
PERIOD_SLEEP  = int(os.getenv('PER_SLEEP', 1000))
CLOUD_USER    = os.getenv('RELAYR_USER')
CLOUD_PASS    = os.getenv('RELAYR_PASS')
CLOUD_DEV     = os.getenv('RELAYR_DEV')
CLOUD_ID      = os.getenv('RESIN_DEVICE_UUID')

if CLOUD_USER is None or CLOUD_PASS is None or CLOUD_DEV is None:
  print "No credentials were found"
  raise

if not os.path.isfile(CLOUD_CERT):
  print "Cert not found at: " + CLOUD_CERT
  raise

print "----------------------------------------------------"
print "Kodama guardian - saving a plant one day at the time"
print "UUID: " + CLOUD_ID
print "sampling at {0}s, publish at {1}s".format(str(PERIOD_SLEEP/1000), str(PERIOD_MEAS/1000))
print "----------------------------------------------------"

cloud = None
is_mqtt_connected = False

# Create the measurements
soil_moist  = Sensor('soil_moist', unit="V", minimum=0, maximum=2500,
                     low_thr=800, hi_thr=2000, low_msg='dry_soil')
temperature = Sensor('temperature', unit="°C", minimum=-10.0, maximum=80.0,
                     low_thr=0.0, hi_thr=40.0, low_msg='too_cold', hi_msg='too_hot')
humidity    = Sensor('humidity', unit="%RH", minimum=0.0, maximum=100.0,
                     low_thr=10.0, hi_thr=100.0)
pressure    = Sensor('pressure', unit="hPa", minimum=800.0, maximum=1300.0,
                     low_thr=800.0, hi_thr=1300.0)

MQTT_MEASUREMENT_MAP = {
  'measurement_mid' : 0,
  'measurements' : {
    'soil' : soil_moist,
    'temp' : temperature,
    'humd' : humidity,
    'atmp' : pressure
  }
}

# This is the dictionary to keep ongoing alerts (other than sensor's)
my_alerts = {
  'alerts' :
  {
    # Sensor failure
    'sensor_failure' : 'clear',
    # No water in the tank
    'no_water'       : 'clear',
    # Flood likely!
    'valve_loose'    : 'clear',
  }
}

# Copy the alerts dictionary into this map to keep track of alerts state changes
MQTT_ALERTS_MAP = {
  'alerts_mid' : 0,
}
MQTT_ALERTS_MAP.update(deepcopy(my_alerts))

# Add sensor specific alerts
for key, value in MQTT_MEASUREMENT_MAP['measurements'].iteritems():
  if value.low_thr_msg is not None:
    MQTT_ALERTS_MAP['alerts'][value.low_thr_msg] = value.alerts[value.low_thr_msg]
  if value.hi_thr_msg is not None:
    MQTT_ALERTS_MAP['alerts'][value.hi_thr_msg]  = value.alerts[value.hi_thr_msg]

# Supported configuration values
MQTT_COMMAND_MAP = {
  # Open the sprinkler
  'water_on'     : None,
  # Enable or Disable managed mode
  'managed_mode' : None
}

print "Alerts: ",
for key, value in MQTT_ALERTS_MAP['alerts'].iteritems():
  print key + " ",
print "\nMeasurements: ",
for key, value in MQTT_MEASUREMENT_MAP['measurements'].iteritems():
  print value.name + " ",
print "\n----------------------------------------------------"

def on_connect(client, userdata, flags, rc):
  global is_mqtt_connected
  if rc == 0:
    is_mqtt_connected = True
    print "Connected to the local MQTT broker, now subscribing..."
    client.subscribe('devices/{0}/commands'.format(CLOUD_DEV), qos=1)
  else:
    is_mqtt_connected = False
    print "Connection failed with RC: " + str(rc)
    raise RuntimeError('Connection failed')

def on_message(client, userdata, msg):
  print json.dumps(msg.payload, indent=4, sort_keys=True)

def on_publish(client, userdata, mid):
  global MQTT_ALERTS_MAP
  print "PUB mid: " + str(mid)

  if MQTT_ALERTS_MAP['alerts_mid'] == mid:
    print "Alert {0} published".format(str(mid))
  elif MQTT_MEASUREMENT_MAP['measurement_mid'] == mid:
    print "Measurement {0} published".format(str(mid))
  else:
    print "Unexpected {0} published".format(str(mid))

def on_disconnect(client, userdata, rc):
  global is_mqtt_connected
  is_mqtt_connected = False
  print "Disconnect RC: " + str(rc)

def on_log(client, userdata, level, buf):
    print "log: ", buf

def stop_mqtt():
  global cloud
  cloud.loop_stop()
  cloud.disconnect()
  sys.exit(0)

def measurements_send():
  global MQTT_MEASUREMENT_MAP
  my_measurements = []
  for key, sensor in MQTT_MEASUREMENT_MAP['measurements'].iteritems():
    if sensor.value is not None:
      data = sensor.pub_json()
      my_measurements.append(data)
  topic = 'devices/{0}/measurements'.format(CLOUD_DEV)
  # print json.dumps(my_measurements, indent=4, sort_keys=True)
  res, MQTT_MEASUREMENT_MAP['measurement_mid'] = cloud.publish(topic, payload=json.dumps(my_measurements),
                                                               qos=1, retain=False)
  if res != 0:
    print "Failed to publish"
  # Schedule this own function again
  threading.Timer(PERIOD_MEAS / 1000, measurements_send).start()

# replace by an iterator and only send alerts when there is a change in its status
def check_alerts():
  global MQTT_ALERTS_MAP

  if not is_mqtt_connected:
    return

  alerts_list = []
  # check first specific sensor alerts
  for key, sensor in MQTT_MEASUREMENT_MAP['measurements'].iteritems():
    an_alert = sensor.is_alert()
    # if the recorded alert is different than the new alert, publish
    if an_alert is not None and MQTT_ALERTS_MAP['alerts'][an_alert] != sensor.alerts[an_alert]:
      MQTT_ALERTS_MAP['alerts'][an_alert] = sensor.alerts[an_alert]
      print "!!!! {0} @ {1} : {2}{3}".format(an_alert, sensor.name, sensor.value, sensor.unit)
      alerts_list.append('{"name":{0}, "state":{1}}'.format(an_alert, MQTT_ALERTS_MAP['alerts'][an_alert]))
  # check other alerts
  for key, state in my_alerts['alerts'].iteritems():
    if state != MQTT_ALERTS_MAP['alerts'][key]:
      MQTT_ALERTS_MAP['alerts'][key] = state
      print "!!!! {0} : {1}".format(key, state)
      alerts_list.append('{"name":{0}, "state":{1}}'.format(key, state))

  if alerts_list:
    topic = 'devices/{0}/alerts'.format(CLOUD_DEV)
    # print json.dumps(my_measurements, indent=4, sort_keys=True)
    res, MQTT_ALERTS_MAP["alerts_mid"] = cloud.publish(topic, payload=json.dumps(alerts_list),
                                         qos=1, retain=False)

def main():
  global cloud, my_alerts
  global MQTT_ALERTS_MAP, MQTT_MEASUREMENT_MAP
  cloud = paho.Client(client_id=CLOUD_ID, clean_session=False)

  cloud.tls_set(CLOUD_CERT)
  cloud.username_pw_set(CLOUD_USER, CLOUD_PASS)

  # Bindings
  cloud.on_log        = on_log
  cloud.on_publish    = on_publish
  cloud.on_connect    = on_connect
  cloud.on_message    = on_message
  cloud.on_disconnect = on_disconnect

  gevent.signal(signal.SIGINT,  stop_mqtt)
  gevent.signal(signal.SIGQUIT, stop_mqtt)
  gevent.signal(signal.SIGTERM, stop_mqtt)
  gevent.signal(signal.SIGKILL, stop_mqtt)

  try:
    cloud.connect(CLOUD_HOST, port=CLOUD_PORT, keepalive=60)
    cloud.loop_start()

    bme280 = BME280()
    soil_hum = SoilMoist()
    chip_id, chip_version = bme280.read_version()

    print "BME280 Chip ID     :", chip_id
    print "BME280 Version     :", chip_version

    # Hard-coded on purpose
    if chip_id != 96:
      print "Unexpected BME280 chip ID, disabling..."
      my_alerts['alerts']['sensor_failure'] = 'set'

    # Run the scheduled routines
    threading.Timer(PERIOD_MEAS / 1000, measurements_send).start()

    # Run the main loop and check for alerts to be published
    while(True):

      soil = soil_hum.read_raw()
      temp, atmp, humd = bme280.read_all()
      MQTT_MEASUREMENT_MAP['measurements']['temp'].is_valid(temp)
      MQTT_MEASUREMENT_MAP['measurements']['humd'].is_valid(humd)
      MQTT_MEASUREMENT_MAP['measurements']['atmp'].is_valid(atmp)
      MQTT_MEASUREMENT_MAP['measurements']['soil'].is_valid(soil)

      print "Soil {0}% @ {1}°C {2}%RH {3}hPa".format(soil, temp, humd, atmp)

      # This will check for alerts to be sent to the cloud
      check_alerts()

      # Wait a bit
      time.sleep(PERIOD_SLEEP / 1000)

  except Exception, e:
    print "Failed to connect!: " + str(e)
    stop_mqtt()
    raise

if __name__=="__main__":
   main()
