package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import java.util.Properties;

public class StreamHub_WeatherService {

    public static void main(String[] args) {
        // the system name (must be unique, gets a consumer-group) and recipients
        final String SYSTEM_NAME = "is.iceland.iot-iot4cps-wp5.WeatherService";
        final String [] OUTPUT_SYSTEMS = {
                "cz.icecars.iot-iot4cps-wp5.CarFleet",
                "at.datahouse.iot-iot4cps-wp5.RoadAnalytics"};
        final String KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:9092";

        // create input and output topics from system name
        final String inputTopicName = SYSTEM_NAME + ".int";
        final String [] outputTopics = new String[OUTPUT_SYSTEMS.length];
        for (int i=0; i<OUTPUT_SYSTEMS.length; i++)
            outputTopics[i] = OUTPUT_SYSTEMS[i] + ".ext";

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
            if (topic.endsWith(".ext"))
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
