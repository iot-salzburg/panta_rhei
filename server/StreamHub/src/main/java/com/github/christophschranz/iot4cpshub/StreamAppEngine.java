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
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Properties;

/** The StreamAppEngine generates streams between Panta Rhei Systems in Kafka, based on System variables
java -jar target/streamApp-1.1-jar-with-dependencies.jar --STREAM_NAME test-jar --SOURCE_SYSTEM is.iceland.iot4cps-wp5-WeatherService.Stations --TARGET_SYSTEM cz.icecars.iot4cps-wp5-CarFleet.Car1 --KAFKA_BOOTSTRAP_SERVERS 192.168.48.179:9092 --GOST_SERVER 192.168.48.179:8082 --FILTER_LOGIC "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;"
*/
public class StreamAppEngine {

    public static void main(String[] args) {
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


        /* *************************        build the Stream Parser class         **************************/
        String expr =  globalOptions.getProperty("FILTER_LOGIC").substring(
                globalOptions.getProperty("FILTER_LOGIC").indexOf(" WHERE ") + 7).replace(";", "");

        Node queryParser = new Node(expr);
        logger.info(queryParser.toString());


        /* *************************        load json from SensorThings         **************************/
        // the json value is not ordered properly, restructure such that we have {iot_id0: {}, iot_id1: {}, ...}
        sensorThingsStreams = new JsonObject();  // set ST to jsonObject

//        // Tests:
//        fetchFromGOST("1"); // -> single fetch, should work
//        fetchFromGOST(9); // -> single fetch, should work
//
//        // test if the entry is available with key 1
//        System.out.println(sensorThingsStreams.get("1").getAsJsonObject());
//
//        fetchFromGOST();  // -> batch fetch, should work
//        fetchFromGOST(31232);  // -> should fail, as the id does not exist


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

        KStream<String, String> filteredStream = inputTopic.filter((k, value) -> check_condition(queryParser, value));
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
     * Check whether or not a msg fulfills the given query or not. Check twice, reload the SensorThings entries
     * if the msg's quantity name can't be found and check a second time.
     * @return boolean whether the msg holds the conditions of the query or not
     */
    public static boolean check_condition(Node queryParser, String inputJson) {
        return check_condition(queryParser, inputJson, false);
    }

    /**
     * Check whether or not a msg fulfills the given query or not. Check twice, reload the SensorThings entries
     * if the msg's quantity name can't be found and check a second time. Parameter second_trial specifies this trial.
     * @return boolean whether the msg holds the conditions of the query or not
     */
    public static boolean check_condition(Node queryParser, String inputJson, boolean second_trial) {
        // json library
        String iot_id = "-1";
        try {
            // parse raw Kafka Message
            JsonObject jsonObject = jsonParser.parse(inputJson).getAsJsonObject();

            iot_id = jsonObject.get("Datastream").getAsJsonObject()
                    .get("@iot.id").getAsString();

            String quantity_name = sensorThingsStreams.get(iot_id).getAsJsonObject().get("name").getAsString();
            jsonObject.addProperty("name", quantity_name);
            logger.info("Getting new (augmented) kafka message: {}", jsonObject);

            boolean queryCondition = queryParser.evaluate(jsonObject);
            logger.debug("Query condition: " + queryCondition);
            return queryCondition;

//            return quantity_name.endsWith(".Station_1.Air Temperature") && result < 10;  // filter on name and condition

        } catch (NullPointerException e) {
            if (!second_trial) {
                logger.info("iot_id '" + iot_id + "' was not found, re-fetching SensorThings.");
                fetchFromGOST(iot_id);
                return check_condition(queryParser, inputJson, true);
            }
            else {
                e.printStackTrace();
                return false;
            }
        }
    }

    /**
     *  fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
     *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
     *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
     *  */
    public static void fetchFromGOST() {
        fetchFromGOST(-1);
    }
    /**
     *  receives the datastream iot_id as String. Trying to convert the String to an Integer and fetching this
     *  datastream from GOST Server. If not possible, all datastreams are fetched.
     *  */
    public static void fetchFromGOST(String iot_id_str) {
        try {
            fetchFromGOST(Integer.parseInt(iot_id_str.trim()));
        } catch (NumberFormatException e) {
            logger.warn("fetchFromGOST, iot_id string couldn't be converted to integer, fetching all datastreams.");
            fetchFromGOST();
        }
    }
    /**
     *  fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
     *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
     *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
     *  */
    public static void fetchFromGOST(int iot_id) {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + globalOptions.getProperty("GOST_SERVER").replace("\"", "");

        if (iot_id <= 0)  // fetching all datastreams for iot_id <= 0
            urlString += "/v1.0/Datastreams";
        else              // fetching a singe datastream
            urlString += "/v1.0/Datastreams(" + iot_id + ")";
//        logger.debug(urlString);

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

            // storing all datastreams
            if (iot_id <= 0) {
                JsonArray rawJsonArray = rawJsonObject.getAsJsonObject().get("value").getAsJsonArray();
                // adding the iot.id: entry mapping to the object
                for (int i = 1; i < rawJsonArray.size(); i++) {
                    logger.info("Adding new datastream with name '" +
                            rawJsonArray.get(i).getAsJsonObject().get("name").getAsString() + "' to mappings.");
                    sensorThingsStreams.add(
                            rawJsonArray.get(i).getAsJsonObject().get("@iot.id").getAsString(),
                            rawJsonArray.get(i).getAsJsonObject());
                }
            }
            // adding only a single datastream
            else {
                JsonObject rawJsonDS = rawJsonObject.getAsJsonObject();
                logger.info("Adding new datastream with name '" + rawJsonDS.get("name").getAsString() +
                        "' to mappings.");
                sensorThingsStreams.add(
                        rawJsonDS.get("@iot.id").getAsString(),
                        rawJsonDS);
            }

        } catch (FileNotFoundException e) {
            logger.error("@iot.id '" + iot_id + "' is not available on SensorThings server '" + urlString + "'.");
            logger.error("Try to restart the client application as it may use a deprecated datastream mapping!");
            System.exit(15);
        } catch (IOException e) {
            // print stack trace but do not exit
            e.printStackTrace();
        }
    }

    /**
     * create required class instances
     */
    public static Properties globalOptions = new Properties();

    public static JsonObject sensorThingsStreams = new JsonObject();

    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);

    public static JsonParser jsonParser = new JsonParser();

}
