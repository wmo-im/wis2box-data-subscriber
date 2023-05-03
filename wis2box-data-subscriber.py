###############################################################################
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
###############################################################################

import os
import json
import sys
import io

from minio import Minio
from urllib.parse import urlparse

from paho.mqtt import client as mqtt

import logging

# gotta log to stdout so docker logs sees the python-logs
logging.basicConfig(stream=sys.stdout)
LOGGER = logging.getLogger('wis2box-data-subscriber')

LOGGING_LOGLEVEL = os.environ.get('LOGGING_LEVEL', 'INFO')
CENTRE_ID = os.environ.get('CENTRE_ID', 'not defined')
COUNTRY_ID = os.environ.get('COUNTRY_ID', 'not defined')
AWS_BROKER = os.environ.get('AWS_BROKER', 'not defined')

MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT')
MINIO_USER = os.environ.get('MINIO_USER')
MINIO_PASSWORD = os.environ.get('MINIO_PASSWORD')
MINIO_BUCKET = os.environ.get('MINIO_BUCKET')
IS_SECURE = False

if MINIO_ENDPOINT.startswith('https://'):
    IS_SECURE = True
    MINIO_ENDPOINT = MINIO_ENDPOINT.replace('https://', '')
else:
    MINIO_ENDPOINT = MINIO_ENDPOINT.replace('http://', '')


def string_array(array):
    """
    function that returns an array of strings out of an array of items
    """

    str_array = []
    for item in array:
        if item is None:
            str_array.append('')
        elif isinstance(item, str):
            str_array.append(f'"{item}"')
        else:
            str_array.append(f'{item}')
    return str_array


def write_csv(topic, headers, logger_id, data):
    """
    function that creates csv
    writes csv content to data-incoming bucket

    :param topic: topic on which data was received written to line 1
    :param headers: headers on which data was received written to line 2
    :param logger_id: logger_id written to line 3
    :param data: data to be split and written to line 4

    :returns: `None`
    """

    minio_client = Minio(
        endpoint=MINIO_ENDPOINT,
        access_key=MINIO_USER,
        secret_key=MINIO_PASSWORD,
        secure=IS_SECURE
    )

    base_csv = f'"{topic}"\n'
    base_csv += f"{','.join(string_array(headers))}\n"
    base_csv += f'"{logger_id}"\n'
    base_csv += '"observations:"\n'

    prefix = f"{COUNTRY_ID}/{CENTRE_ID}"
    prefix += "/data/core/weather/surface-based-observations/synop/"

    # create one csv per timestamp
    for timestamp in data.keys():
        my_csv = base_csv
        my_data = string_array(data[timestamp])
        my_csv += f"{','.join(my_data)}\n"
        csv_bytes = my_csv.encode('utf-8')
        csv_buffer = io.BytesIO(csv_bytes)
        ts_id = timestamp
        ts_id = ts_id.replace(':', '')
        ts_id = ts_id.replace('-', '')
        identifier = f"{prefix}{logger_id}_{ts_id}.csv"
        try:
            LOGGER.info(f"Upload csv to endpoint={MINIO_ENDPOINT}")
            minio_client.put_object(
                MINIO_BUCKET,
                identifier,
                csv_buffer,
                len(csv_bytes))
        except Exception as e:
            LOGGER.error(e)
        LOGGER.info(f"Successfully uploaded {identifier} to {MINIO_BUCKET}")


def process_data(client, userdata, msg):
    """
    function executed 'on_message' for paho.mqtt.client
    inspects the message and uploads csv content to data-incoming bucket

    :param client: client-object associated to 'on_message'
    :param userdata: MQTT-userdata
    :param msg: MQTT-message-object received by subscriber

    :returns: `None`
    """

    topic = msg.topic
    LOGGER.info(f"Message received on topic={topic}.")
    m = json.loads(msg.payload.decode('utf-8'))
    last_level = topic.split('/')[-1]
    if last_level == "SYNOP":
        try:
            write_csv(topic,
                      headers=m['properties']['observationNames'],
                      logger_id=m['properties']['loggerID'],
                      data=m['properties']['observations'])
        except Exception as e:
            LOGGER.error(f"ERROR writing csv from MQTT-message received: {e}")
    else:
        LOGGER.info(f"{last_level} != SYNOP, skip data")


def sub_data_incoming(client, userdata, flags, rc, properties=None):
    """
    function executed 'on_connect' for paho.mqtt.client
    subscribes to data-incoming/#

    :param client: client-object associated to 'on_connect'
    :param userdata: userdata
    :param flags: flags
    :param rc: return-code received 'on_connect'
    :param properties: properties

    :returns: `None`
    """
    LOGGER.info(f"connected: {mqtt.connack_string(rc)}")
    for s in ["data-incoming/#"]:
        LOGGER.info(f'subscribe to: {s}')
        client.subscribe(s, qos=1)


def main():
    """
    Subscribe to data-incoming and dump data as csv
    """

    print(f"LOGGING_LOGLEVEL={LOGGING_LOGLEVEL}")
    LOGGER.setLevel(LOGGING_LOGLEVEL)

    if COUNTRY_ID == 'not defined':
        LOGGER.error("COUNTRY_ID is not defined, exiting")
        return
    if CENTRE_ID == 'not defined':
        LOGGER.error("CENTRE_ID is not defined, exiting")
        return
    if AWS_BROKER == 'not defined':
        LOGGER.error("WIS2BOX_BROKER_PUBLIC is not defined, exiting")
        return

    broker_url = urlparse(AWS_BROKER)

    try:
        LOGGER.info("setup connection")
        LOGGER.info(f"host={broker_url.hostname}")
        LOGGER.info(f"user={broker_url.username}")
        LOGGER.info(f"port={broker_url.port}")
        client_id = f"wis2box-data-subscriber-{COUNTRY_ID}-{CENTRE_ID}"
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
        client.on_connect = sub_data_incoming
        client.on_message = process_data
        client.username_pw_set(broker_url.username, broker_url.password)
        if broker_url.scheme == 'mqtts':
            LOGGER.info("mqtts: set tls_version=2")
            client.tls_set(tls_version=2)
        client.connect(broker_url.hostname, broker_url.port)
        client.loop_forever()
    except Exception as err:
        LOGGER.error(f"Failed to setup MQTT-client with error: {err}")


if __name__ == '__main__':
    main()
