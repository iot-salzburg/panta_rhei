package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;
import java.util.Set;

/* The StreamAppEngine generates streams between Panta Rhei Systems in Kafka, based on System variables */
public class StreamAppEngine {

    public static void main(String[] args) {
        final Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

        /* *************************   fetching the parameters and check them    **************************/
        logger.info("Starting a new stream with the parameter:");

        if (System.getenv().containsKey("STREAM_NAME"))
            globalOptions.setProperty("stream-name", System.getenv("STREAM_NAME"));
        if (System.getenv().containsKey("SOURCE_SYSTEM"))
            globalOptions.setProperty("source-system", System.getenv("SOURCE_SYSTEM"));
        if (System.getenv().containsKey("TARGET_SYSTEM"))
            globalOptions.setProperty("target-system", System.getenv("TARGET_SYSTEM"));
        if (System.getenv().containsKey("KAFKA_BOOTSTRAP_SERVERS"))
            globalOptions.setProperty("bootstrap-server", System.getenv("KAFKA_BOOTSTRAP_SERVERS"));
        if (System.getenv().containsKey("FILTER_LOGIC"))
            globalOptions.setProperty("filter-logic", System.getenv("FILTER_LOGIC"));

        // parse input parameter to options and check completeness, must be a key-val pair
        if (1 == args.length % 2) {
            logger.error("Error: Expected key val pairs as arguments.");
            logger.error("Usage: java -jar path/to/streamhub_apps.jar --key1 val1 .. --keyN valN");
            System.exit(2);
        }
        for (int i=0; i<args.length; i+=2){
            String key = args[i].replace("--", "");
            globalOptions.setProperty(key, args[i+1]);
        }

        String[] keys = {"stream-name", "source-system", "target-system", "bootstrap-server", "filter-logic"};
        for (String key: keys) {
            if (!globalOptions.stringPropertyNames().contains(key)) {
                logger.error("Error: You have to define the parameter " + key +
                        " either as environment variable or pass it in the arguments.");
                logger.error("Usage: java -jar path/to/streamhub_apps.jar --key1 val1 .. --keyN valN");
                System.exit(3);
            }
            logger.info("  " + key + ": " + globalOptions.getProperty(key));
        }

//        System.exit(99);

        /**************************   set up the topology and then start it    **************************/
        // create input and output topics from system name
        String inputTopicName = globalOptions.getProperty("source-system") + ".int";
        String targetTopic = globalOptions.getProperty("target-system") + ".ext";

        // create properties
        Properties properties = new Properties();
        properties.setProperty(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, globalOptions.getProperty("bootstrap-server"));
        properties.setProperty(StreamsConfig.APPLICATION_ID_CONFIG, "streamhub-" +
                globalOptions.getProperty("source-system") + "." + globalOptions.getProperty("stream-name"));
        properties.setProperty(StreamsConfig.DEFAULT_KEY_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());
        properties.setProperty(StreamsConfig.DEFAULT_VALUE_SERDE_CLASS_CONFIG, Serdes.StringSerde.class.getName());

        // create topology
        StreamsBuilder streamsBuilder = new StreamsBuilder();

        // input topic, application logic
        KStream<String, String> inputTopic = streamsBuilder.stream(inputTopicName);

        // TODO apply filter logic
        KStream<String, String> filteredStream = inputTopic.filter((k, value) -> check_where_condition(value));

        filteredStream.to(targetTopic);

        // build the topology
        KafkaStreams kafkaStreams = new KafkaStreams(
                streamsBuilder.build(),
                properties);

        // start our streams application
        kafkaStreams.start();
    }

    public static Properties globalOptions = new Properties();

    public static JsonParser jsonParser = new JsonParser();

    public static boolean check_where_condition(String inputJson) {
        // json library
        try {
            System.out.println(inputJson);
            String logic = globalOptions.getProperty("filter_logic");
            int iot_id;
            double result;
            iot_id = jsonParser.parse(inputJson)
                    .getAsJsonObject()
                    .get("Datastream").getAsJsonObject()
                    .get("@iot.id").getAsInt();
            result = jsonParser.parse(inputJson)
                    .getAsJsonObject()
                    .get("result").getAsDouble();
//            return quantity.endsWith(".Station_1.Air Temperature") && result < 10;
            System.out.println(result < 10);
            return result < 10;
        } catch (NullPointerException e) {
            e.printStackTrace();
            return false;
        }
    }
}
