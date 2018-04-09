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

from sensors_wrapper import Sensors
import paho.mqtt.client as paho

CLOUD_HOST = "cloud-mqtt.relayr.io"
CLOUD_CERT = "cacert.pem"
CLOUD_PORT = 8883

# Values set in resin.io ENV VARS
PERIOD_MEAS   = int(os.getenv('PER_MEAS', 30000))
PERIOD_SLEEP  = int(os.getenv('PER_SLEEP', 1000))

CLOUD_USER    = os.getenv('RELAYR_USER')
CLOUD_PASS    = os.getenv('RELAYR_PASS')
CLOUD_DEV     = os.getenv('RELAYR_DEV')
CLOUD_ID      = os.getenv('RESIN_DEVICE_UUID')

cloud = None
is_mqtt_connected = False

if CLOUD_USER is None or CLOUD_PASS is None or CLOUD_DEV is None:
  raise SystemExit("No credentials were found")

def print_banner():
  print "----------------------------------------------------"
  print "Kodama guardian - saving a plant one day at the time"
  print "UUID: " + CLOUD_ID
  print "sampling at {0}s, publish at {1}s".format(str(PERIOD_SLEEP/1000), str(PERIOD_MEAS/1000))
  print "----------------------------------------------------"

def on_connect(client, userdata, flags, rc):
  global is_mqtt_connected
  if rc == 0:
    is_mqtt_connected = True
    print "Connected to the local MQTT broker, now subscribing..."
    client.subscribe('devices/{0}/commands'.format(CLOUD_DEV), qos=1)
  else:
    is_mqtt_connected = False
    raise RuntimeError("Connection failed with RC: " + str(rc))

def on_message(client, userdata, msg):
  print json.dumps(msg.payload, indent=4, sort_keys=True)

def on_publish(client, userdata, mid):
  global MQTT_ALERTS_MAP
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

def send_measurements():
  topic = 'devices/{0}/measurements'.format(CLOUD_DEV)
  # print json.dumps(my_measurements, indent=4, sort_keys=True)
  res, MQTT_MEASUREMENT_MAP['measurement_mid'] = cloud.publish(topic, payload=json.dumps(my_measurements),
                                                               qos=1, retain=False)
  if res != 0:
    print "Failed to publish"
  # Schedule this own function again
  threading.Timer(PERIOD_MEAS / 1000, send_measurements).start()

def send_alerts():
  if not is_mqtt_connected:
    return

  if alerts_list:
    topic = 'devices/{0}/alerts'.format(CLOUD_DEV)
    # print json.dumps(my_measurements, indent=4, sort_keys=True)
    res, MQTT_ALERTS_MAP["alerts_mid"] = cloud.publish(topic, payload=json.dumps(alerts_list),
                                         qos=1, retain=False)

def main():
  global cloud

  # test the two well-known locations of this file
  if os.path.isfile(os.path.join(sys.path[0], CLOUD_CERT)):
    certh_path = os.path.join(sys.path[0], CLOUD_CERT)
  elif os.path.isfile(os.path.join("/usr/src/app/src", CLOUD_CERT)):
    certh_path = os.path.join("/usr/src/app/src", CLOUD_CERT)
  else:
    raise SystemExit("Certificate not found")

  cloud = paho.Client(client_id=CLOUD_ID, clean_session=False)

  cloud.tls_set(certh_path)
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
  except Exception, e:
    stop_mqtt()
    raise SystemExit("Failed to connect!: " + str(e))

  plant_sensors = Sensors("measurements.yaml")

  # Run the scheduled routines
  threading.Timer(PERIOD_MEAS / 1000, send_measurements).start()

  # Run the main loop and check for alerts to be published
  while(True):
    plant_sensors.read_sensors()
    print(plant_sensors)

    # This will check for alerts to be sent to the cloud
    send_alerts()

    # Wait a bit
    time.sleep(PERIOD_SLEEP / 1000)

if __name__=="__main__":
   main()
