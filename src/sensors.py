#!/usr/bin/python
# -*- coding: utf-8 -*-
#--------------------------------------
import os
import sys
import json
import gevent
import signal
import time
import datetime

from bme280 import BME280
from soil import SoilMoist

import paho.mqtt.client as paho

CLOUD_HOST = "cloud-mqtt.relayr.io"
CLOUD_CERT = "/usr/src/app/src/cacert.pem"
CLOUD_PORT = 8883

# Values set in resin.io ENV VARS
SLEEP_MS   = os.getenv('SLEEP_MS', 30000)
CLOUD_USER = os.getenv('RELAYR_USER')
CLOUD_PASS = os.getenv('RELAYR_PASS')
CLOUD_DEV  = os.getenv('RELAYR_DEV')
CLOUD_ID   = os.getenv('RESIN_DEVICE_UUID')

if CLOUD_USER is None or CLOUD_PASS is None or CLOUD_DEV is None:
  print "No credentials were found"
  raise

if not os.path.isfile(CLOUD_CERT):
  print "Cert not found at: " + CLOUD_CERT
  raise

# Device measurements
MQTT_MEASUREMENT_MAP = {
  'soil_moist'  : None,
  'temperature' : None,
  'humidity'    : None,
  'pressure'    : None
}

# Supported configuration values
MQTT_COMMAND_MAP = [
    # Open the sprinkler
    'water_on',
    # Enable or Disable managed mode
    'managed_mode'
]

# List of alerts:
# "no_water", "valve_loose", "dry_soil"

cloud = None

def on_connect(client, userdata, flags, rc):
  if rc == 0 and MQTT_COMMAND_MAP:
    print "Connected to the local MQTT broker, now subscribing..."
    client.subscribe('device/{0}/commands'.format(CLOUD_DEV))
  else:
    print "Connection failed with RC: " + str(rc)
    raise RuntimeError('Connection failed')


def on_message(client, userdata, msg):
  pass

def on_publish(client, userdata, mid):
  print "PUB mid: " + str(mid)

def on_disconnect(client, userdata, rc):
  print "Disconnect RC: " + str(rc)

def stop_mqtt():
  global cloud
  cloud.loop_stop()
  cloud.disconnect()

  sys.exit(0)

def main():

  # make cloud client
  global cloud
  global MQTT_MEASUREMENT_MAP
  cloud = paho.Client(client_id=CLOUD_ID, clean_session=False)

  cloud.tls_set(CLOUD_CERT)
  cloud.username_pw_set(CLOUD_USER, CLOUD_PASS)

  # Bindings
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

    # A bit of hacky-magik because why not...
    time.sleep(5)

    while(True):

      soil = soil_hum.read_raw()
      temperature, pressure, humidity = bme280.read_all()

      print "Soil {0}% @ {1}°C {2}%RH {3}hPa".format(soil, temperature, humidity, pressure)

      # Ugly
      MQTT_MEASUREMENT_MAP['soil_moist']  = soil
      MQTT_MEASUREMENT_MAP['temperature'] = temperature
      MQTT_MEASUREMENT_MAP['humidity']    = humidity
      MQTT_MEASUREMENT_MAP['pressure']    = pressure

      # Create a list of measurements
      my_measurements = []
      for key, value in MQTT_MEASUREMENT_MAP.iteritems():
        if value is not None:
          timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%m:%S.%f')[0:-3] + 'Z'
          data = { "name":key, "value":value, "recorded":timestamp }
          my_measurements.append(data)
      topic = 'devices/{0}/measurements'.format(CLOUD_DEV)
      cloud.publish(topic, payload = json.dumps(my_measurements), qos=1, retain=False)

      # Wait a bit
      time.sleep(int(SLEEP_MS) / 1000)

  except Exception, e:
    print "Failed to connect!: " + str(e)
    stop_mqtt()
    raise

if __name__=="__main__":
   main()
