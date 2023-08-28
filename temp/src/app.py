#!/usr/bin/python3
# -*- coding: utf-8 -*-

from time import time, sleep, ctime
import adafruit_dht
import board
import paho.mqtt.client as mqtt
import json
from statistics import median

MQTT_HOST   = '192.168.1.11'
MQTT_PORT   = 1883
MQTT_USER   = 'rasp'
MQTT_PASS   = 'smoothme'
DHT_PIN     = board.D4 # BCM 4 == GPIO 7
BIAS_TEMP   = 1.00290
BIAS_HUMI   = 0.95686
SLEEP       = 10

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = '0000000000000000'
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = 'ERROR000000000'

    return cpuserial

ME = 'RP3-{}'.format(getserial())
STATE = 'homeassistant/sensor/{}/state'.format(ME)
STATUS = 'homeassistant/sensor/{}/status'.format(ME)
DEVICE_INFO = {
    'identifiers': getserial(),
    'manufacturer': 'Alex Inc.',
    'model': 'Raspi Sensor',
    'name': ME
}

config = [
    {'topic': 'homeassistant/sensor/{}/temperature/config'.format(ME), 'payload': json.dumps({
        'name': '{}_temperature'.format(ME),
        'unique_id': '{}_temperature'.format(ME),
        'state_topic': STATE,
        'device_class': 'temperature',
        'unit_of_measurement': '°C',
        'value_template': '{{ value_json.temperature }}',
        'force_update': True,
        'device': DEVICE_INFO,
        'availability_topic': STATUS,
        'payload_available': 'online',
        'payload_not_available': 'offline'
    })},
    {'topic': 'homeassistant/sensor/{}/humidity/config'.format(ME), 'payload': json.dumps({
        'name': '{}_humidity'.format(ME),
        'unique_id': '{}_humidity'.format(ME),
        'state_topic': STATE,
        'device_class': 'humidity',
        'unit_of_measurement': '%',
        'value_template': '{{ value_json.humidity }}',
        'force_update': True,
        'device': DEVICE_INFO,
        'availability_topic': STATUS,
        'payload_available': 'online',
        'payload_not_available': 'offline'
    })},
    {'topic': 'homeassistant/sensor/{}/timeouts/config'.format(ME), 'payload': json.dumps({
        'name': '{}_timeouts'.format(ME),
        'unique_id': '{}_timeouts'.format(ME),
        'state_topic': STATE,
        'value_template': '{{ value_json.timeouts }}',
        'device': DEVICE_INFO,
        'availability_topic': STATUS,
        'payload_available': 'online',
        'payload_not_available': 'offline'
    })}
]

def on_publish(client, userdata, msg):
    print('Sent message: {}'.format(msg))

def on_connect(client, userdata, flags, rc):
    print('Connected with result code {}'.format(rc))

    client.publish(STATUS, 'online', 0, False)


client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.on_connect = on_connect
client.on_publish = on_publish
client.will_set(STATUS, 'offline', 0, False)

client.connect(MQTT_HOST, MQTT_PORT, 60)

client.loop_start()

# Wait till we're connected
while not client.is_connected():
    sleep(1)

for c in config:
    client.publish(c['topic'], c['payload'], 0, True)

dhtDevice = adafruit_dht.DHT22(DHT_PIN)

print('Finished config')
# a little delay to allow HA to process the config message
sleep(1)
print('Starting loop')

timeouts = 0
# preT = preRH = 0
TEMP = []
HUMI = []
while True:
    # RH, T = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, DHT_PIN)
    try:
        T = dhtDevice.temperature
        RH = dhtDevice.humidity
    except RuntimeError as error:
        print(error.args[0])
        T = None
        RH = None

    t = ctime(time())
    if T:
        T = T * BIAS_TEMP
        RH = RH * BIAS_HUMI
        if not (-40 <= float(T) <= 80):
            print('{}: Temperature out of bounds, {:0.2f} C'.format(t, T))
            continue
        if not (0 <= float(RH) <= 100):
            print('{}: Humidity out of bounds, {:0.2f} %'.format(t, RH))
            continue
        # if preT != 0 and abs((T-preT)/preT) > 0.1:
        #     print('{}: Temperature changed too much, last value was {:0.2f} C and new one is {:0.2f} C. Discarding.'.format(t, preT, T))
        #     continue
        # if preRH != 0 and abs((RH-preRH)/preRH) > 0.1:
        #     print('{}: Humidity changed too much, last value was {:0.2f} % and new one is {:0.2f} %. Discarding.'.format(t, preRH, RH))
        #     continue
        timeouts = 0
        print('{}: {:0.2f} C, {:0.2f} %'.format(t, T, RH))

        TEMP.append(T)
        HUMI.append(RH)
    else:
        timeouts += 1
        print('{}: timeout error'.format(t))

    if len(TEMP) == 3:
        data = {
            'temperature': round(median(TEMP), 1),
            'humidity': int(median(HUMI)),
            'timeouts': timeouts
        }
        TEMP = []
        HUMI = []

        # preT = T
        # preRH = RH
    elif timeouts >= 3:
        data = {
            'timeouts': timeouts
        }
    else:
        data = None

    if data:
        client.publish(STATE, json.dumps(data), 0, False)
        print('{}: {}'.format(STATE, json.dumps(data)))
        client.publish(STATUS, 'online', 0, False)

    sleep(SLEEP)

client.loop_stop()
