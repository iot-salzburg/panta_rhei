package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.apache.kafka.common.serialization.Serdes;
import org.apache.kafka.streams.KafkaStreams;
import org.apache.kafka.streams.StreamsBuilder;
import org.apache.kafka.streams.StreamsConfig;
import org.apache.kafka.streams.kstream.KStream;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.KeyException;
import java.util.Properties;
import java.util.concurrent.TimeUnit;


/* The StreamAppEngine generates streams between Panta Rhei Systems in Kafka, based on System variables */
public class StreamAppEngine {

    public static void main(String[] args) {
        final Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

        /* *************************   fetching the parameters and check them    **************************/
        logger.info("Starting a new stream with the parameter:");

        if (System.getenv().containsKey("STREAM_NAME"))
            globalOptions.setProperty("STREAM_NAME", System.getenv("STREAM_NAME"));
        if (System.getenv().containsKey("SOURCE_SYSTEM"))
            globalOptions.setProperty("SOURCE_SYSTEM", System.getenv("SOURCE_SYSTEM"));
        if (System.getenv().containsKey("TARGET_SYSTEM"))
            globalOptions.setProperty("TARGET_SYSTEM", System.getenv("TARGET_SYSTEM"));
        if (System.getenv().containsKey("KAFKA_BOOTSTRAP_SERVERS"))
            globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", System.getenv("KAFKA_BOOTSTRAP_SERVERS"));
        if (System.getenv().containsKey("GOST_SERVER"))
            globalOptions.setProperty("GOST_SERVER", System.getenv("GOST_SERVER"));
        if (System.getenv().containsKey("FILTER_LOGIC"))
            globalOptions.setProperty("FILTER_LOGIC", System.getenv("FILTER_LOGIC"));

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

        String[] keys = {"STREAM_NAME", "SOURCE_SYSTEM", "TARGET_SYSTEM", "KAFKA_BOOTSTRAP_SERVERS",
                "GOST_SERVER", "FILTER_LOGIC"};
        for (String key: keys) {
            if (!globalOptions.stringPropertyNames().contains(key)) {
                logger.error("Error: You have to define the parameter " + key +
                        " either as environment variable or pass it in the arguments.");
                logger.error("Usage: java -jar path/to/streamhub_apps.jar --key1 val1 .. --keyN valN");
                System.exit(3);
            }
            logger.info("  " + key + ": " + globalOptions.getProperty(key));
        }


        /**************************        load json from SensorThings         **************************/

        reloadGOSTServer();
        String name = sensorThingsStreams.get(Integer.toString(58)).getAsJsonObject().get("name").getAsString();
        System.out.println(name);

//        System.exit(99);

        /**************************   set up the topology and then start it    **************************/
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

        // TODO apply filter logic
        KStream<String, String> filteredStream = inputTopic.filter((k, value) -> check_condition(value));

        filteredStream.to(targetTopic);

        // build the topology
        KafkaStreams kafkaStreams = new KafkaStreams(
                streamsBuilder.build(),
                properties);

        // start our streams application
        kafkaStreams.start();
    }

    public static Properties globalOptions = new Properties();

    public static JsonObject sensorThingsStreams = new JsonObject();

    public static JsonParser jsonParser = new JsonParser();

    public static boolean check_condition(String inputJson) {
        return check_condition(inputJson, false);
    }

    public static boolean check_condition(String inputJson, boolean second_try) {
        // json library
        String iot_id = "-1";
        try {
            System.out.println("Getting new kafka message: " + inputJson);
            String logic = globalOptions.getProperty("FILTER_LOGIC");  // TODO apply logic
            double result;
            iot_id = jsonParser.parse(inputJson)
                    .getAsJsonObject()
                    .get("Datastream").getAsJsonObject()
                    .get("@iot.id").getAsString();

            String quantity_name = sensorThingsStreams.get(iot_id).getAsJsonObject().get("name").getAsString();
            System.out.println("  Quantity is: " + quantity_name);

            result = jsonParser.parse(inputJson)
                    .getAsJsonObject()
                    .get("result").getAsDouble();

            return quantity_name.endsWith(".Station_1.Air Temperature") && result < 10;  // filter on name and condition

        } catch (NullPointerException e) {
            if (!second_try) {
                System.out.println("iot_id '" + iot_id + "' was not found, refetching sensorthings.");
                reloadGOSTServer();
                return check_condition(inputJson, true);
            }
            else {
                e.printStackTrace();
                return false;
            }
        }
    }

    /* reload GOST Server entries into json, forward with -1 if no iot_id is specified */
    public static void reloadGOSTServer() {
        reloadGOSTServer(-1);
    }
    public static void reloadGOSTServer(int iot_id) {
        if (iot_id == -1) {
            String urlString = "http://" + globalOptions.getProperty("GOST_SERVER").replace("\"", "");
            urlString += "/v1.0/Datastreams";
//            System.out.println(urlString);
            StringBuilder result = new StringBuilder();

        try {
            URL url = new URL(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            BufferedReader rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
            String line;
            while ((line = rd.readLine()) != null) {
                result.append(line);
            }
            rd.close();
            JsonElement rawJsonObject = jsonParser.parse(result.toString());
            JsonArray rawJsonArray = rawJsonObject.getAsJsonObject().get("value").getAsJsonArray();

            // the json value is not ordered properly, restructure such that we have {iot_id0: {}, iot_id1: {}, ...}
            sensorThingsStreams = new JsonObject();  // set ST to jsonObject

            for (int i=1; i < rawJsonArray.size(); i++ ) {
                System.out.println("Adding " + rawJsonArray.get(i).getAsJsonObject().get("name").getAsString());
                sensorThingsStreams.add(
                        rawJsonArray.get(i).getAsJsonObject().get("@iot.id").getAsString(),
                        rawJsonArray.get(i).getAsJsonObject());
            }

        } catch (IOException e) {
            e.printStackTrace();
        }
        } else {
            System.out.println("Iot id was specified, however, not implemented yet.");
            System.exit(5);
        }
    }
}
