
import requests
import time

from paho.mqtt import client as mqtt

from urllib.parse import urlparse

broker_url = urlparse('mqtt://wis2box@localhost:5883')
filename = 'test/test-data/message.json'
topic = 'data-incoming/zmb/campbell-v1/MetDpt-WIS2Test/data/cr1000x/34769/SYNOP'
# connect to local MQTT and publish message
with open(filename,'r') as f:
    message = f.read()
    client = mqtt.Client(client_id="test", protocol=mqtt.MQTTv5)
    client.username_pw_set(broker_url.username, broker_url.password)
    client.connect('localhost', broker_url.port)
    print("publish test-message")
    client.publish(topic=topic,payload=message)

# wait 2 seconds and then check file has been created
print('wait 2 seconds')
time.sleep(2)
print('check file is in bucket')
mypath = 'zm-zmb_met_centre/data/core/weather/surface-based-observations/synop'
myfilename = 'CR1000X_34769_20230428T153200Z.csv'
res = requests.get(f'http://localhost:9000/wis2box-incoming/{mypath}/{myfilename}')
print(res)
# raise exception in case of failure
res.raise_for_status()
print("success!")