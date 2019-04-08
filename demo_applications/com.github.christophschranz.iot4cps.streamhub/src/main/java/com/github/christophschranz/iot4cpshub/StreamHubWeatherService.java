package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import java.util.Properties;

public class StreamHubWeatherService {

    public static void main(String[] args) {
        // write constants
        final String SYSTEM_NAME = "weather-service";  // must be unique (gets a consumergroup)
        final String INPUT_TOPIC = "eu.srfg.iot-iot4cps-wp5.weather-service.data";
        final String [] OUTPUT_TOPICS = {"eu.srfg.iot-iot4cps-wp5.car1.external",
                "eu.srfg.iot-iot4cps-wp5.car2.external"};

        // create properties
        Properties properties = new Properties();
        properties.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "127.0.0.1:9092");
        properties.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "streamhub-" + SYSTEM_NAME);
        properties.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        properties.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());

        // create topology
        StreamsBuilder streamsBuilder = new StreamsBuilder();

        // input topic, application logic
        KStream<String, String> inputTopic = streamsBuilder.stream(INPUT_TOPIC);
        KStream<String, String> filteredStream = inputTopic.filter((k, jsonTweet) -> true);

        for (String topic: OUTPUT_TOPICS)
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

    public static int extractUserFollowersInTweet(String tweetJson) {
        // json library
        try {
            return jsonParser.parse(tweetJson)
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
