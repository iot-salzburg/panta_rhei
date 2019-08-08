#!/usr/bin/env bash

# Create default topics for the demonstrator
echo "Create new topics:"
# docker exec -it $(docker ps |grep confluentinc/cp-enterprise-kafka | awk '{print $1}') bash -c "kafka-topics --zookeeper zookeeper:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet.data > /dev/null 2>&1 || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.CarFleet.data > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.CarFleet.external > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.CarFleet.logging > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.WeatherService.data > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.WeatherService.external > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.WeatherService.logging > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.InfraProv.data > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.InfraProv.external > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.srfg.iot-iot4cps-wp5.InfraProv.logging > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"

# List the topics
echo
echo "List of all topics:"
/kafka/bin/kafka-topics.sh --zookeeper :2181 --list
