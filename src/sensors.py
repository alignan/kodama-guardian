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

from measurement import Sensor
from bme280 import BME280
from soil import SoilMoist

import paho.mqtt.client as paho

CLOUD_HOST = "cloud-mqtt.relayr.io"
CLOUD_CERT = "/usr/src/app/src/cacert.pem"
CLOUD_PORT = 8883

# Values set in resin.io ENV VARS
PERIOD_MEAS   = os.getenv('PER_MEAS', 30000)
PERIOD_SLEEP  = os.getenv('PER_SLEEP', 1000)
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

# Create the measurements
soil_moist  = Sensor('soil_moist', unit="V", minimum=0, maximum=2500, low_thr=800, hi_thr=2000)
temperature = Sensor('temperature', unit="°C", minimum=-10.0, maximum=80.0, low_thr=0.0, hi_thr=40.0)
humidity    = Sensor('humidity', unit="%RH", minimum=0.0, maximum=100.0, low_thr=10.0, hi_thr=100.0)
pressure    = Sensor('pressure', unit="hPa", minimum=800.0, maximum=1300.0, low_thr=800.0, hi_thr=1300.0)

MQTT_MEASUREMENT_MAP = {
  'soil' : soil_moist,
  'temp' : temperature,
  'humd' : humidity,
  'atmp' : pressure
}

# Supported alerts
MQTT_ALERTS_MAP = {
  # Alert state has changed
  'alert_change' : False,
  'alerts' :
  {
    # Sensor failure
    'sensor_failure' : 'clear',
    # No water in the tank
    'no_water'       : 'clear',
    # Flood likely!
    'valve_loose'    : 'clear',
    # Soil dry below recommended threshold
    'dry_soil'       : 'clear'
  }
}

# Supported configuration values
MQTT_COMMAND_MAP = {
  # Open the sprinkler
  'water_on'     : None,
  # Enable or Disable managed mode
  'managed_mode' : None
}

cloud = None

def set_alert(key_val):
  global MQTT_ALERTS_MAP
  MQTT_ALERTS_MAP['alert_change'] = True
  MQTT_ALERTS_MAP['alerts'][key_val] = 'set'

def clear_alert(key_val):
  global MQTT_ALERTS_MAP
  MQTT_ALERTS_MAP['alert_change'] = True
  MQTT_ALERTS_MAP['alerts'][key_val] = 'clear'

def on_connect(client, userdata, flags, rc):
  if rc == 0:
    print "Connected to the local MQTT broker, now subscribing..."
    client.subscribe('devices/{0}/commands'.format(CLOUD_DEV), qos=1)
  else:
    print "Connection failed with RC: " + str(rc)
    raise RuntimeError('Connection failed')

def on_message(client, userdata, msg):
  pass

def on_publish(client, userdata, mid):
  print "PUB mid: " + str(mid)

def on_disconnect(client, userdata, rc):
  print "Disconnect RC: " + str(rc)

def on_log(client, userdata, level, buf):
    print "log: ", buf

def stop_mqtt():
  global cloud
  cloud.loop_stop()
  cloud.disconnect()

  sys.exit(0)

def measurements_send():
  my_measurements = []
  for key, sensor in MQTT_MEASUREMENT_MAP.iteritems():
    if sensor.value is not None:
      data = sensor.pub_json()
      my_measurements.append(data)
  topic = 'devices/{0}/measurements'.format(CLOUD_DEV)
  # print json.dumps(my_measurements, indent=4, sort_keys=True)
  cloud.publish(topic, payload=json.dumps(my_measurements), qos=1, retain=False)

  # Schedule this own function again
  threading.Timer(int(PERIOD_MEAS) / 1000, measurements_send).start()

def main():
  global cloud
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
      set_alert('sensor_failure')

    # Run the scheduled routines
    measurements_send()

    # Run the main loop and check for alarms to be published
    while(True):

      soil = soil_hum.read_raw()
      temp, atmp, humd = bme280.read_all()
      MQTT_MEASUREMENT_MAP['temp'].is_valid(temp)
      MQTT_MEASUREMENT_MAP['humd'].is_valid(humd)
      MQTT_MEASUREMENT_MAP['atmp'].is_valid(atmp)
      MQTT_MEASUREMENT_MAP['soil'].is_valid(soil)

      print "Soil {0}% @ {1}°C {2}%RH {3}hPa".format(soil, temp, humd, atmp)

      for key, sensor in MQTT_MEASUREMENT_MAP.iteritems():
        alarm = sensor.is_alarm()
        if alarm is not None:
          print "!!!! {0} @ {1} : {2}{3}".format(alarm, sensor.name, sensor.value, sensor.unit)

      # Wait a bit
      time.sleep(int(PERIOD_SLEEP) / 1000)

  except Exception, e:
    print "Failed to connect!: " + str(e)
    stop_mqtt()
    raise

if __name__=="__main__":
   main()
