# wis2box-data-subscriber

Service to subscribe to data published by Automatic Weather Stations and store the data into the wis2box-incoming bucket. It is currently designed to in conjuction with the 'csv2bufr'-plugin and the default mapping-template 'synop_bufr.json' .

## how it works

The wis2box-data-subscriber subscribes to the topic 'data-incoming/#' to a broker-endpoint configured by the environment variables.

The wis2box-data-subscriber checks that the last level of the topic is 'SYNOP', before proceeding to process the data.

One .csv is created per timestamp for the content of the 'observations'-object in the message. The the attribute 'observationNames' is written as the headers into each .csv.

The .csv is stored as new object into the MINIO-endpoint defined by the environment variables for this services. The path used for the file in the minio-bucket is defined as:

`{COUNTRY_ID}/{CENTRE_ID}/data/core/weather/surface-based-observations/synop/`

Where COUNTRY_ID and CENTRE_ID are defined with environment variables.

Processing non-synop data will required an updated version of the current code.

See /test for example.

## Environment variables

wis2box-data-subscriber uses. the following environment-variables:

```bash

AWS_BROKER=mqtt://wis2box:xxx@localhost:1883 # set endpoint for broker where AWS data is published
COUNTRY_ID=zmb # set country_id used in wis2-topic-hierarchy
CENTRE_ID=zmb_met_centre # set centre_id for wis2-topic-hierarchy
LOGGING_LEVEL=INFO # set logging level

LOGGING_LEVEL=INFO # set logging-level
MINIO_BUCKET=wis2box-incoming
MINIO_ENDPOINT=http://localhost:9000 # set this to the minio-endpoint for your wis2box 
MINIO_ROOT_USER=minio # minio username for your minio-endpoint
MINIO_ROOT_PASSWORD=xxx # minio password for your minio-endpoint
```
