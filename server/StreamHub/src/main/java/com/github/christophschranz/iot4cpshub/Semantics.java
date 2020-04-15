package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Properties;

public class Semantics {
    String stream_name;
    String source_system;
    String target_system;
    String kafka_bootstrap_servers;
    String gost_server;
    String filter_logic;

    JsonObject sensorThingsStreams;
    String semantic;
    String[] knownSemantics = new String[] {"SensorThings"};
    String[] augmentedAttributes = new String[]{"name"};  // those attributes are stored as String only

    /**
     The Semantics constructor. Requires a stream app config, fetches and stores the required metadata for incoming
     jsonInputs
     */
    public Semantics(Properties stream_config, String semantic) throws SemanticsException {
        // gather configs and store in class vars
        this.stream_name = stream_config.getProperty("STREAM_NAME").replace("\"", "");
        this.source_system = stream_config.getProperty("SOURCE_SYSTEM").replace("\"", "");
        this.target_system = stream_config.getProperty("TARGET_SYSTEM").replace("\"", "");
        this.kafka_bootstrap_servers = stream_config.getProperty("KAFKA_BOOTSTRAP_SERVERS").replace("\"", "");
        this.gost_server = stream_config.getProperty("GOST_SERVER").replace("\"", "");
        this.filter_logic = stream_config.getProperty("FILTER_LOGIC").replaceAll("\\x00", "");
        this.semantic = semantic;

        // Check the if the Semantic is supported, throw an exception otherwise
        boolean flag_isKnown = false;
        for (String knownSemantic: this.knownSemantics)
            if (knownSemantic.equals(semantic)) {
                flag_isKnown = true;
                break;
            }
        if (!flag_isKnown) {
            logger.error("Unknown semantic '" + semantic + "'. Choose one of:");
            for (String knownSemantic: this.knownSemantics)
                logger.error(" * " + knownSemantic);
            throw new SemanticsException("Semantic '" + semantic + "' is not known.");
        }

        // Check if the GOST server is reachable
        checkConnectionGOST();

        // the json value is not indexed properly, restructure such that we have {iot_id0: {}, iot_id1: {}, ...}
        this.sensorThingsStreams = new JsonObject();  // set ST to jsonObject
//        // Tests:
//        fetchFromGOST("1"); // -> single fetch, should work
//        fetchFromGOST(9); // -> single fetch, should work
//        System.out.println(sensorThingsStreams.get("1").getAsJsonObject());
//        fetchFromGOST();  // -> batch fetch, should work
//        fetchFromGOST(31232);  // -> should fail, as the id does not exist

        logger.info("New " + semantic + "-semantic initialized.");
        logger.info(this.toString());
    }

    /** toString-method
     * @return some information about the StreamQuery.
     */
    public String toString(){
        return "Semantics Object " + getClass()
                + "\n\tType: \t\t" + this.semantic
                + "\n\tServer: \t" + this.gost_server
                + "\n\tEntries: \t" + this.sensorThingsStreams.size();
    }

    /**
     * This method parses the raw String input and augments it with attributes specified in the argument
     * @return the Augmented JsonInput
     */
    public JsonObject augmentRawInput(String input) {
        // receive input string and parse to jsonObject
        return augmentJsonInput(jsonParser.parse(input).getAsJsonObject());
    }

    /**
     * This method augments the raw JsonObject input with attributes specified in the argument
     * @return the Augmented JsonInput
     */
    public JsonObject augmentJsonInput(JsonObject jsonInput) {
        // receive input string and parse to jsonObject

        String iot_id = jsonInput.get("Datastream").getAsJsonObject().get("@iot.id").getAsString();
        try {
            if (sensorThingsStreams.get(iot_id) == null) {
                fetchFromGOST(iot_id);
            }
        } catch (SemanticsException e) {
            e.printStackTrace();
        }

        String quantity;
        for (String att: this.augmentedAttributes) {
            quantity = sensorThingsStreams.get(iot_id).getAsJsonObject().get(att).getAsString();
            jsonInput.addProperty(att, quantity);
        }

        logger.debug("Getting new (augmented) kafka message: {}", jsonInput);
        return jsonInput;
    }

    /**
     *  fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
     *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
     *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
     *  */
    public void fetchFromGOST() throws SemanticsException {
        fetchFromGOST(-1);
    }
    /**
     *  receives the datastream iot_id as String. Trying to convert the String to an Integer and fetching this
     *  datastream from GOST Server. If not possible, all datastreams are fetched.
     *  */
    public void fetchFromGOST(String iot_id_str) throws SemanticsException {
        try {
            fetchFromGOST(Integer.parseInt(iot_id_str.trim()));
        } catch (NumberFormatException | SemanticsException e) {
            logger.warn("fetchFromGOST, iot_id string couldn't be converted to integer, fetching all datastreams.");
            fetchFromGOST();
        }
    }

    /**
     *  Checks the connection to the SensorThings Server and throws an error if not reachable
     *  */
    public void checkConnectionGOST() throws SemanticsException {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + this.gost_server;
//        urlString = this.gost_server;
        try {
            URL url = new URL(urlString);
            System.out.println(urlString);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            BufferedReader rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
        } catch (Exception e) {
            // print stack trace but do not exit
            throw new SemanticsException("The SensorThings Server " + this.gost_server + " is not reachable.");
        }
    }

        /**
         *  Fetches all datastreams from GOST Server and stores the mapping of the form iot.id: entry
         *  (hash-indexed) into a jsonObject, such that the entry is available with complexity O(1).
         *  default parameter -1 triggers to fetch all entries, as it is useful at the startup.
         *  */
    public void fetchFromGOST(int iot_id) throws SemanticsException {
        // urlString that is appended by the appropriate mode (all ds or a specified)
        String urlString = "http://" + this.gost_server;

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
                    this.sensorThingsStreams.add(
                            rawJsonArray.get(i).getAsJsonObject().get("@iot.id").getAsString(),
                            rawJsonArray.get(i).getAsJsonObject());
                }
            }
            // adding only a single datastream
            else {
                JsonObject rawJsonDS = rawJsonObject.getAsJsonObject();
                logger.info("Adding new datastream with name '" + rawJsonDS.get("name").getAsString() +
                        "' to mappings.");
                this.sensorThingsStreams.add(
                        rawJsonDS.get("@iot.id").getAsString(),
                        rawJsonDS);
            }

        } catch (FileNotFoundException e) {
            logger.error("@iot.id '" + iot_id + "' is not available on SensorThings server '" + urlString + "'.");
            logger.error("Try to restart the client application as it may use a deprecated datastream mapping!");
            throw new SemanticsException("@iot.id '" + iot_id + "' was not found on SensorThings server '" + urlString + "'.");
        } catch (IOException e) {
            // print stack trace but do not exit
            e.printStackTrace();
        }
    }

    /**
     * create required class instances
     */
    public static Logger logger = LoggerFactory.getLogger(Semantics.class);

    public static JsonParser jsonParser = new JsonParser();
}
