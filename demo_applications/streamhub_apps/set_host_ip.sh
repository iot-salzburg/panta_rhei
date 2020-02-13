#!/usr/bin/env bash
export HOST_IP=$(hostname -I | cut -d' ' -f1)
export STREAM_NAME="test-stream"
export SOURCE_SYSTEM=is.iceland.iot4cps-wp5-WeatherService.Stations
export TARGET_SYSTEM=cz.icecars.iot4cps-wp5-CarFleet.Car1
export KAFKA_BOOTSTRAP_SERVERS=${HOST_IP}:9092
export GOST_SERVER=${HOST_IP}:8082
export FILTER_LOGIC="SELECT 'Station_1.Air Temperature' FROM is.iceland.iot4cps-wp5-WeatherService.Stations
       WHERE 'Station_1.Air Temperature' < 4;"