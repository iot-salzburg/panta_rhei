package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;

import java.util.Properties;

public class Tester {

        public static void main(String[] args) {
                globalOptions.setProperty("STREAM_NAME", "test-stream");
                globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
                globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
                globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", "192.168.48.179:9092");
                globalOptions.setProperty("GOST_SERVER", "192.168.48.179:8082");
                globalOptions.setProperty("FILTER_LOGIC",
                        "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;");

                JsonObject jsonInput = new JsonObject();
                jsonInput.addProperty("name", "Station_1.Air Temperature");
                jsonInput.addProperty("result", 12.3);
                jsonInput.addProperty("phenomenonTime", "2020-02-24T11:26:02");
                jsonInput.addProperty("time", "2020-02-24T11:26:02");  // adding extra time key

                String expr;
//                expr = "name = 'Station_1.Air Temperature'";
//                Node anode = new Node(expr);
//                System.out.println(anode);
//                System.out.println(anode.isTrue(jsonInput));
//                System.out.println();
//
//                expr =  "20 > result";
//                anode = new Node(expr);
//                System.out.println(anode);
//                System.out.println(anode.isTrue(jsonInput));
//                System.out.println();
//
//                expr =  "result < 20";
//                anode = new Node(expr);
//                System.out.println(anode);
//                System.out.println(anode.isTrue(jsonInput));
//                System.out.println();
//
//                expr =  "time > '2020-04-23T11:26:02'";
//                anode = new Node(expr);
//                System.out.println(anode);
//                System.out.println(anode.isTrue(jsonInput));
//                System.out.println();

                System.out.println("#######################################################\n");

                Node node;

                expr =  "name = 'Station_1.Air Temperature' AND result > 4";
                node = new Node(expr);

//                System.out.println(node.isTrue(jsonInput));
//                System.out.println();

                // recursive tests:
                expr =  "name = 'Station_1.Air Temperature'";
                expr =  "name == 'Station_1.Air Temperature'";  // must fail
                expr =  "name = 'Station_1.Air Temperature' OR result > 4";
                expr =  "(name = 'Station_1.Air Temperature' OR result > 4)";
                expr =  "name = 'Station_1.Air Temperature' OR (result > 30 AND result > 4)";
                expr =  "((name = 'Station_1.Air Temperature' OR (((result < 30) AND result > 4))))";
                expr =  "(name = 'Station_1.Air Temperature' OR name = 'Station_2.Air Temperature') AND ((result < 30) AND result > 4)";  // must fail
                expr =  "(result < 30 AND result < 4) OR name = 'Station_1.Air Temperature'";

                expr =  "result < 30 AND result < 4 OR name = 'Station_1.Air Temperature'";  // should be equal than the one above
                expr =  "result > 0 XOR name = 'Station_1.Air Temperature'";  // intro of XOR
                expr =  "result = 0 XOR name = 'Station_1.Air Temperature'";  // intro of XOR
                expr =  "name <> 'Station_1.Air Temperature'";  // intro of not equal, false
                expr =  "name <> 'Station_123.Air Temperature'";  // intro of not equal, true

                expr =  "NOT result > 30";  // intro of not, true
                expr =  " NOT NOT result > 30";  // intro of not, false
                expr =  "result < 30 AND NOT name = 'Station_123.Air Temperature'";  // intro of not, true
                expr =  "NOT (result < 30 AND NOT name = 'Station_1.Air Temperature')";  // intro of not, false
                expr =  "NOT NOT (result < 30 AND NOT NOT name = 'Station_1.Air Temperature')";  // intro of not, true

                // ordering and hierarchy
                expr =  "result < 30 AND result > 4 AND name = 'Station_1.Air Temperature' ";  // true
                expr =  "result > 30 AND result > 4 AND name = 'Station_1.Air Temperature' ";  // false
                expr =  "result < 30 AND result > 4 AND name <> 'Station_1.Air Temperature' ";  // false
                expr =  "result > 30 AND result > 4 XOR name = 'Station_1.Air Temperature' ";  // true
                expr =  "name = 'Station_1.Air Temperature' XOR result > 30 AND result > 4";  // ordering, true
                expr =  "result > 30 AND result > 4 OR name = 'Station_123.Air Temperature'";  // false
                expr =  "name = 'Station_123.Air Temperature' OR result > 30 AND result > 4";  // false


//                node = new Node(expr);
//                System.out.println(node);
//                System.out.println(node.evaluate(jsonInput));


                System.out.println("#######################################################\n");


                globalOptions.setProperty("STREAM_NAME", "test-stream");
                globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
                globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
                globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", "192.168.48.179:9092");
                globalOptions.setProperty("GOST_SERVER", "192.168.48.179:8082");
                globalOptions.setProperty("FILTER_LOGIC",
                        "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;");


//                StreamQuery stream_parser = new StreamQuery(globalOptions);
//                System.out.println(stream_parser);
//                System.out.println(stream_parser.evaluate(jsonInput));

                LogicalNode logNode = new LogicalNode(expr);
                System.out.println(logNode);
                System.out.println(logNode.getDegree());
                System.out.println(logNode.evaluate(jsonInput));
        }

        public static Properties globalOptions = new Properties();

}
