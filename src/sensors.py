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

script_dir = os.path.dirname(__file__)

CLOUD_HOST = "cloud-mqtt.relayr.io"
CLOUD_CERT = os.path.join(script_dir, "cacert.pem")
CLOUD_PORT = 8883

# Values set in resin.io ENV VARS
SLEEP_MS   = os.getenv('SLEEP_MS', 30000)
CLOUD_USER = os.getenv('RELAYR_USER')
CLOUD_PASS = os.getenv('RELAYR_PASS')
CLOUD_DEV  = os.getenv('RELAYR_DEV')

if CLOUD_DEV is None or CLOUD_PASS is None or CLOUD_DEV is None:
  print "No credentials were found"
  raise

SUBSCRIPTIONS = []

# Device and readings map (ID, name and value)
MQTT_CLOUD_MAP = [
    # soil moisture
    (CLOUD_DEV, 'soil_moist'),
    # temperature
    (CLOUD_DEV, 'temperature'),
    # humidity
    (CLOUD_DEV, 'humidity'),
    # atmospheric pressure
    (CLOUD_DEV, 'pressure')
]

cloud = None

def on_connect(client, userdata, flags, rc):
    global SUBSCRIPTIONS

    if rc == 0:
        print "Connected to the local MQTT broker"

        if SUBSCRIPTIONS:
            client.subscribe(SUBSCRIPTIONS)
    else:
        print "Connection failed!"
        raise RuntimeError('Connection failed')


def on_message(client, userdata, msg):
    pass

def stop_mqtt():
    global cloud
    cloud.loop_stop()
    cloud.disconnect()

    sys.exit(0)

def main():

  # make cloud client
  global cloud
  cloud = paho.Client()
  cloud.tls_set(CLOUD_CERT)
  cloud.username_pw_set(CLOUD_USER, CLOUD_PASS)

  gevent.signal(signal.SIGINT,  stop_mqtt)
  gevent.signal(signal.SIGQUIT, stop_mqtt)
  gevent.signal(signal.SIGTERM, stop_mqtt)
  gevent.signal(signal.SIGKILL, stop_mqtt)

  # populate topics
  for item in MQTT_CLOUD_MAP:
    SUBSCRIPTIONS.append( ('devices/{}/measurement/{}'.format(item[0], item[1]), 0) )

  try:
    cloud.connect(CLOUD_HOST, CLOUD_PORT)
    cloud.loop_start()

    bme280 = BME280()
    soil_hum = SoilMoist()
    chip_id, chip_version = bme280.read_version()

    print "BME280 Chip ID     :", chip_id
    print "BME280 Version     :", chip_version

    while(True):

      soil = soil_hum.read_raw()
      temperature, pressure, humidity = bme280.read_all()

      print "Soil {0}% @ {1}°C {2}%RH {3}hPa".format(soil, temperature, humidity, pressure)

      MEAS = []
      MEAS.append(soil)
      MEAS.append(temperature)
      MEAS.append(humidity)
      MEAS.append(pressure)

      for index, value in enumerate(MQTT_CLOUD_MAP):

        try:

          topic = 'devices/{}/measurements'.format(MQTT_CLOUD_MAP[index][0])
          timestamp = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%m:%S.%f')[0:-3] + 'Z'

          data = {
            'name': MQTT_CLOUD_MAP[index][1],
            'value': MEAS[index],
            'recorded': timestamp
          }

          cloud.publish(topic, payload = json.dumps([data]), qos=0, retain=False)

        except IndexError:
          print "Out of bound!"
          pass

      # Wait a bit
      time.sleep(int(SLEEP_MS) / 1000)

  except Exception, e:
    print "Failed to connect!: " + str(e)
    stop_mqtt()
    raise

if __name__=="__main__":
   main()
