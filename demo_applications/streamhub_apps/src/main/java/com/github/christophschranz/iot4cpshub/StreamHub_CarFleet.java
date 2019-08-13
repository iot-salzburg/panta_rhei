package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import java.util.Properties;

public class StreamHub_CarFleet {

    public static void main(String[] args) {
        // the system name (must be unique, gets a consumer-group) and recipients
        final String SYSTEM_NAME = "at.srfg.iot-iot4cps-wp5.CarFleet";
        final String [] OUTPUT_SYSTEMS = {"at.srfg.iot-iot4cps-wp5.InfraProv"};
        final String KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092";

        // create input and output topics from system name
        final String inputTopicName = SYSTEM_NAME + ".data";
        final String [] outputTopics = new String[OUTPUT_SYSTEMS.length];
        for (int i=0; i<OUTPUT_SYSTEMS.length; i++)
            outputTopics[i] = OUTPUT_SYSTEMS[i] + ".external";

        // create properties
        Properties properties = new Properties();
        properties.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, KAFKA_BOOTSTRAP_SERVERS);
        properties.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "streamhub-" + SYSTEM_NAME);
        properties.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        properties.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());

        // create topology
        StreamsBuilder streamsBuilder = new StreamsBuilder();

        // input topic, application logic
        KStream<String, String> inputTopic = streamsBuilder.stream(inputTopicName);
        KStream<String, String> filteredStream = inputTopic.filter((k, jsonTweet) -> true);

        for (String topic: outputTopics)
            if (topic.contains("external"))
                filteredStream.to(topic);
            else
                System.out.println("Check the OUTPUT_TOPICS: " + topic);

        // build the topology
        KafkaStreams kafkaStreams = new KafkaStreams(
                streamsBuilder.build(),
                properties);

        // start our streams application
        kafkaStreams.start();
    }

    public static JsonParser jsonParser = new JsonParser();

    public static int extractInfo(String inputJson) {
        // json library
        try {
            return jsonParser.parse(inputJson)
                    .getAsJsonObject()
                    .get("user")
                    .getAsJsonObject()
                    .get("followers_count")
                    .getAsInt();
        } catch (NullPointerException e) {
            return 0;
        }
    }
}
