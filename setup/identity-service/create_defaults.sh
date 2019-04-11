#!/usr/bin/env bash

# Create default topics for the demonstrator
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.data > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.external > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.logging > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet2.data > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet2.external > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet2.logging > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.WeatherService.data > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.WeatherService.external > /dev/null 2>&1 || echo Topic was already created"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.WeatherService.logging > /dev/null 2>&1 || echo Topic was already created"

# List the topics
echo
echo "List of created topics:"
docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') kafka-topics --zookeeper zookeeper:2181 --list
