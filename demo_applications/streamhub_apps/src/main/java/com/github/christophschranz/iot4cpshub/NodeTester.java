package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;

import java.util.Arrays;
import java.util.Properties;

public class NodeTester {

        public static void main(String[] args) {
                globalOptions.setProperty("STREAM_NAME", "test-stream");
                globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
                globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
                globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", "192.168.48.179:9092");
                globalOptions.setProperty("GOST_SERVER", "192.168.48.179:8082");
                globalOptions.setProperty("FILTER_LOGIC",
                        "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations " +
                                "WHERE name = 'Station_1.Air Temperature' AND result < 4");

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

                expr =  "name = 'Station_1.Air Temperature' AND result > 4";
//                Node node = new Node(expr);
//                System.out.println(node.isTrue(jsonInput));
//                System.out.println();

                // recursive test
                expr =  "name = 'Station_1.Air Temperature' OR result > 4";
                expr =  "(name = 'Station_1.Air Temperature' OR result > 4)";
                expr =  "name = 'Station_1.Air Temperature' OR (result > 30 AND result > 4)";
                expr =  "((name = 'Station_1.Air Temperature' OR (((result < 30) AND result > 4))))";
                expr =  "(name = 'Station_1.Air Temperature' OR name = 'Station_2.Air Temperature') AND ((result < 30) AND result > 4)";
                expr =  "(result < 30 AND result > 4) OR name = 'Station_1.Air Temperature'";
                Node node = new Node(expr);
                System.out.println(node.isTrue(jsonInput));
                System.out.println();

                String str = "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations " +
                        "WHERE name = 'is.iceland.iot4cps-wp5-WeatherService.Station_1.Air Temperature' AND result < 0;";

                System.out.println(str.substring(str.indexOf(" WHERE ") + 7).replace(";", ""));
        }

        public static Properties globalOptions = new Properties();

}

