package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

/**
 * Class representing the stream Parser object of the app and has refers to the root node.
 */
public class StreamQuery {
    String stream_name;
    String source_system;
    String target_system;
    String kafka_bootstrap_servers;
    String gost_server;
    String filter_logic;

    Node query_tree;
    String projection_list;
    String cps_list;
    String condition;

    /**
    The StreamParser constructor. Requires a stream app config, extracts the parts of the filter_logic and builds a
     NodeTree for the condition query.
     */
    public StreamQuery(Properties stream_config) {
        final String KEY_WORDS = "(SELECT |FROM |WHERE |;)";
        this.stream_name = stream_config.getProperty("STREAM_NAME");
        this.source_system = stream_config.getProperty("SOURCE_SYSTEM");
        this.target_system = stream_config.getProperty("TARGET_SYSTEM");
        this.kafka_bootstrap_servers = stream_config.getProperty("KAFKA_BOOTSTRAP_SERVERS");
        this.gost_server = stream_config.getProperty("GOST_SERVER");
        this.filter_logic = stream_config.getProperty("FILTER_LOGIC").replaceAll("\\x00","");

        // extract the filter_logic and do validations
        // SELECT projection_list FROM cps_list WHERE selection_conditions;
        // SELECT [*| att1,att2,...] FROM [*|cps1,cps2,...] WHERE [condition];
        // (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;

        // Extract the parts from the filter_logic and check if the expression is valid
        if (!(this.filter_logic.contains("SELECT ") && filter_logic.contains("FROM "))) {
            logger.error("filter_logic doesn't contain keywords 'SELECT' and/or 'FROM'.");
            System.exit(101);
        }
        // split on specific keyword and fetch until next arbitrary key word
        this.projection_list = this.filter_logic.substring(this.filter_logic.indexOf("SELECT ") + 7).
                split(KEY_WORDS)[0].trim();
        this.cps_list = this.filter_logic.substring(this.filter_logic.indexOf("FROM ") + 5).
                split(KEY_WORDS)[0].trim();
        if (this.filter_logic.contains("WHERE "))
            condition = this.filter_logic.substring(this.filter_logic.indexOf("WHERE ") + 6).
                    split(KEY_WORDS)[0].trim();
        else
            condition = "TRUE";
        logger.info("projection_list: '" + projection_list + "'");
        logger.info("cps_list: '" + cps_list + "'");
        logger.info("condition: '" + condition + "'");

        // build the conditional expression via a node tree
        if (!condition.equals("TRUE"))
            this.query_tree = new Node(condition);
    }

    /**
     * Return a boolean expression whether the jsonInput data point is evaluated by the expression as true or false.
     * This works recursively by traversing the Nodes down to the leaf nodes.
     * @return boolean expression
     */
    public boolean evaluate(JsonObject jsonInput) {
        if (this.condition.equals("TRUE"))
            return true;
        else
            return this.query_tree.evaluate(jsonInput);
    }

    /**
     * Property object for the stream app config
     */
    public static Properties stream_config = new Properties();

    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);
}
