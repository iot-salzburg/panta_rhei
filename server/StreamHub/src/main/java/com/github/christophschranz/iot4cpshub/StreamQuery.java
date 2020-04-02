package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Properties;

/**
 * Class representing the stream Parser object of the app and has refers to the root node.
 */
public class StreamQuery {
    final String KEY_WORDS = "(SELECT |FROM |WHERE |;)";

    String stream_name;
    String source_system;
    String target_system;
    String kafka_bootstrap_servers;
    String gost_server;
    String filter_logic;

    LogicalNode conditionTree;
    String projection_list;
    String cps_list;
    String condition;

    /**
    The StreamParser constructor. Requires a stream app config, extracts the parts of the filter_logic and builds a
     NodeTree for the condition query.
     */
    public StreamQuery(Properties stream_config) throws StreamSQLException {
        // gather configs and store in class vars
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
        if (!safeContainsKeyword(this.filter_logic, "SELECT "))
            throw new StreamSQLException("The filter_logic doesn't contain keyword 'SELECT'.");
        if (!safeContainsKeyword(this.filter_logic,"FROM "))
            throw new StreamSQLException("The filter_logic doesn't contain keyword 'FROM'.");

        // split on specific keyword and fetch until next arbitrary key word
        this.projection_list = this.filter_logic.substring(this.filter_logic.indexOf("SELECT ") + 7).
                split(KEY_WORDS)[0].trim();
        this.cps_list = this.filter_logic.substring(this.filter_logic.indexOf("FROM ") + 5).
                split(KEY_WORDS)[0].trim();
        if (safeContainsKeyword(this.filter_logic,"WHERE "))
            this.condition = this.filter_logic.substring(this.filter_logic.indexOf("WHERE ") + 6).
                    split(KEY_WORDS)[0].trim();
        else  // set condition to TRUE, if there is no WHERE filter
            condition = "TRUE";
        logger.info("projection_list: '" + projection_list + "'");
        logger.info("cps_list: '" + cps_list + "'");
        logger.info("condition: '" + condition + "'");

        // augment the condition with the full expressions from possible AS statements

        // build the conditional expression via a node tree
        this.conditionTree = new LogicalNode(condition);
    }

    /** toString-method
     * @return some information about the StreamQuery.
     */
    public String toString(){
        return "StreamQuery Object " + getClass()
                + "\n\tStream name: \t\t" + this.stream_name
                + "\n\tSource system: \t\t" + this.source_system
                + "\n\tTarget system: \t\t" + this.target_system
                + "\n\tKafka servers: \t\t" + this.kafka_bootstrap_servers
                + "\n\tGOST server: \t\t" + this.gost_server
                + "\n\tProjection List: \t" + this.projection_list
                + "\n\tCPS List: \t\t\t" + this.cps_list
                + "\n\tCondition Node: \t" + this.condition;
    }
    /**
     * Return a boolean expression whether the jsonInput data point is evaluated by the expression as true or false.
     * This works recursively by traversing the Nodes of the conditionTree down to the leaf nodes.
     * @return boolean expression
     */

    public boolean evaluate(String input) {
        return evaluate(jsonParser.parse(input).getAsJsonObject());
    }
    public boolean evaluate(JsonObject jsonInput) {
        if (this.condition.equals("TRUE"))  // return true directly as it is faster
            return true;
        try {
            return this.conditionTree.evaluate(jsonInput);
        } catch (StreamSQLException e) {
            e.printStackTrace();
        }
        return false;
    }

    /**
     * Secure return whether the expr contains a keyword or not, it ignores keywords in quotes
     * @return boolean whether the expr contains a keyword or not
     */
    public static boolean safeContainsKeyword(String expr, String keyword) throws StreamSQLException {
        // copy all chars that are not in quotes to new char array
        int expr_i = 0;  // idx for str
        int res_i = 0;  // idx for outerString generation
        boolean isInQuotes = false;
        char[] ca = new char[expr.length()];
        while (expr_i<expr.length()) {
            if (expr.charAt(expr_i) == '\'')
                isInQuotes = !isInQuotes;
            if (!isInQuotes) {
                ca[res_i] = expr.charAt(expr_i);
                res_i ++;
            }
            expr_i ++;
        }
        // correct invalid number of quotes
        if (isInQuotes)
            throw new  StreamSQLException("Query is invalid, odd number of single quotes: " + expr);

        // create new String from resulting char array and check if the arithmetic key word is in it
        String outerString = String.valueOf(ca);
        return outerString.contains(keyword);
    }
    /**
     * Property object for the stream app config
     */
    public static Properties stream_config = new Properties();

    public static JsonParser jsonParser = new JsonParser();

    public static Logger logger = LoggerFactory.getLogger(StreamAppEngine.class);
}
