package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import java.util.Optional;
import java.util.Properties;

//STREAM_NAME="whoami"
//SYSTEM_NAME="cz.icecars.iot-iot4cps-wp5.CarFleet"
//TARGET_SYSTEM="at.datahouse.iot-iot4cps-wp5.RoadAnalytics"
//KAFKA_BOOTSTRAP_SERVERS="127.0.0.1:9092"
// input parameters
// --stream-name whoami --source-system cz.icecars.iot-iot4cps-wp5.CarFleet --target-system at.datahouse.iot-iot4cps-wp5.RoadAnalytics --bootstrap-server 127.0.0.1:9092 --filter-logic {}

public class StreamEngine {

    public static void main(String[] args) {
        System.out.println("Starting a new stream with the parameters:");
        // parse input to options and check completeness
        if ((args.length == 0) || (1 == args.length % 2)) {
            System.out.println("Error: Expected key val pairs as arguments.");
            System.exit(2);
        }
        Properties options = new Properties();
        for (int i=0; i<args.length; i+=2){
            String key = args[i].replace("--", "");
            options.setProperty(key, args[i+1]);
            System.out.println("Got option: " + key + " = " + options.getProperty(key));
        }
        System.out.println(options.stringPropertyNames());
        String[] keys = {"stream-name", "source-system", "target-system", "bootstrap-server", "filter-logic"};
        for (String key: keys) {
            if (!options.stringPropertyNames().contains(key)) {
                System.out.println("Error: You have to define the parameter " + key);
                System.exit(3);
            }
        }


        // create input and output topics from system name
        String inputTopicName = options.getProperty("source-system") + ".int";
        String targetTopic = options.getProperty("target-system") + ".ext";

        // create properties
        Properties properties = new Properties();
        properties.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, options.getProperty("bootstrap-server"));
        properties.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "streamhub-" + options.getProperty("source-system") + "." + options.getProperty("stream-name"));
        properties.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        properties.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());

        // create topology
        StreamsBuilder streamsBuilder = new StreamsBuilder();

        // input topic, application logic
        KStream<String, String> inputTopic = streamsBuilder.stream(inputTopicName);
        KStream<String, String> filteredStream = inputTopic.filter((k, jsonTweet) -> true);

        // TODO apply filter logic
        if (targetTopic.endsWith(".ext"))
            filteredStream.to(targetTopic);
        else
            System.out.println("Check the OUTPUT_TOPICS: " + targetTopic);

//        filteredStream.to(targetTopic);

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
