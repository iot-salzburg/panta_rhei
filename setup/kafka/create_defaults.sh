#!/usr/bin/env bash

# Create default topics for the demonstrator
echo "Create new topics:"

sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.int > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.ext > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.log > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car1.int > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car1.ext > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car1.log > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car2.int > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car2.ext > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic cz.icecars.iot4cps-wp5-CarFleet.Car2.log > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic is.iceland.iot4cps-wp5-WeatherService.Stations.int > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic is.iceland.iot4cps-wp5-WeatherService.Stations.ext > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"
sh -c "(/kafka/bin/kafka-topics.sh --zookeeper :2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic is.iceland.iot4cps-wp5-WeatherService.Stations.log > /dev/null 2>&1 && echo A new topic was created ) || echo Topic was already created"

# List the topics
echo
echo "List of all topics:"
/kafka/bin/kafka-topics.sh --zookeeper :2181 --list
