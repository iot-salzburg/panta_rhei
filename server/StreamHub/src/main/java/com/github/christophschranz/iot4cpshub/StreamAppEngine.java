package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.Properties;

/** The StreamAppEngine generates streams between Panta Rhei Systems in Kafka, based on System variables
java -jar target/streamApp-1.1-jar-with-dependencies.jar --STREAM_NAME test-jar --SOURCE_SYSTEM is.iceland.iot4cps-wp5-WeatherService.Stations --TARGET_SYSTEM cz.icecars.iot4cps-wp5-CarFleet.Car1 --KAFKA_BOOTSTRAP_SERVERS 192.168.48.179:9092 --GOST_SERVER 192.168.48.179:8082 --FILTER_LOGIC "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;"
*/
public class StreamAppEngine {

    public static void main(String[] args) throws StreamSQLException, SemanticsException {
        final Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

        /* *************************   fetching the parameters and check them    **************************/
        logger.info("Starting a new stream with the parameter:");

        if (System.getenv().containsKey("STREAM_NAME"))
            globalOptions.setProperty("STREAM_NAME",
                    System.getenv("STREAM_NAME").replaceAll("\"", ""));
        if (System.getenv().containsKey("SOURCE_SYSTEM"))
            globalOptions.setProperty("SOURCE_SYSTEM", System.getenv("SOURCE_SYSTEM"));
        if (System.getenv().containsKey("TARGET_SYSTEM"))
            globalOptions.setProperty("TARGET_SYSTEM", System.getenv("TARGET_SYSTEM"));
        if (System.getenv().containsKey("KAFKA_BOOTSTRAP_SERVERS"))
            globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", System.getenv("KAFKA_BOOTSTRAP_SERVERS"));
        if (System.getenv().containsKey("GOST_SERVER"))
            globalOptions.setProperty("GOST_SERVER", System.getenv("GOST_SERVER"));
        if (System.getenv().containsKey("FILTER_LOGIC"))
            globalOptions.setProperty("FILTER_LOGIC",
                    System.getenv("FILTER_LOGIC").replaceAll("\"", ""));
        // env vars: STREAM_NAME="test-stream";SOURCE_SYSTEM=is.iceland.iot4cps-wp5-WeatherService.Stations;
        // TARGET_SYSTEM=cz.icecars.iot4cps-wp5-CarFleet.Car1;KAFKA_BOOTSTRAP_SERVERS=127.0.0.1:9092;
        // GOST_SERVER=127.0.0.1:8082;
        // FILTER_LOGIC="SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30\;"

        // parse input parameter to options and check completeness, must be a key-val pair
        if (1 == args.length % 2) {
            logger.error("Error: Expected key val pairs as arguments.");
            logger.error("Usage: java -jar path/to/streamhub_apps.jar --key1 val1 .. --keyN valN");
            System.exit(11);
        }
        for (int i=0; i<args.length; i+=2){
            String key = args[i].replace("--", "");
            globalOptions.setProperty(key, args[i+1]);
        }

        String[] keys = {"STREAM_NAME", "SOURCE_SYSTEM", "TARGET_SYSTEM", "KAFKA_BOOTSTRAP_SERVERS",
                "GOST_SERVER", "FILTER_LOGIC"};
        for (String key: keys) {
            if (!globalOptions.stringPropertyNames().contains(key)) {
                logger.error("Error: You have to define the parameter " + key +
                        " either as environment variable or pass it in the arguments.");
                logger.error("Usage: java -jar path/to/streamhub_apps.jar --key1 val1 .. --keyN valN");
                System.exit(12);
            }
            logger.info("  " + key + ": " + globalOptions.getProperty(key));
        }


        /* *************************        create the Stream Query class         **************************/
        StreamQuery streamQuery = new StreamQuery(globalOptions);

        /* *************************        create the Semantics class         **************************/
        Semantics semantics = new Semantics(globalOptions, "SensorThings");


        /* *************************   set up the topology and then start it    **************************/
        // create input and output topics from system name
        String inputTopicName = globalOptions.getProperty("SOURCE_SYSTEM") + ".int";
        String targetTopic = globalOptions.getProperty("TARGET_SYSTEM") + ".ext";

        // create properties
        Properties properties = new Properties();
        properties.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, globalOptions.getProperty("KAFKA_BOOTSTRAP_SERVERS"));
        properties.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "streamhub-" +
                globalOptions.getProperty("SOURCE_SYSTEM") + "." + globalOptions.getProperty("STREAM_NAME"));
        properties.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        properties.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());

        // create topology
        StreamsBuilder streamsBuilder = new StreamsBuilder();

        // input topic, application logic
        KStream<String, String> inputTopic = streamsBuilder.stream(inputTopicName);

        // Evaluate value to true to forward the input or false
        KStream<String, String> filteredStream = inputTopic.filter((k, value) ->
                                                        streamQuery.evaluate(semantics.augmentRawInput(value)));

//        KStream<String, String> filteredStream = inputTopic.filter((k, value) -> true);

        filteredStream.to(targetTopic);

        // build the topology
        KafkaStreams kafkaStreams = new KafkaStreams(
                streamsBuilder.build(),
                properties);

        // start our streams application
        kafkaStreams.start();

    }

    /**
     * create required class instances
     */
    public static Properties globalOptions = new Properties();

}
