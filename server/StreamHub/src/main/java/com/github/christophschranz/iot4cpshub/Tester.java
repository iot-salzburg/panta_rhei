package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;

import java.io.IOException;
import java.util.ArrayList;
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
                LogicalNode logNode;
                ComparisonNode comNode;
                ArithmeticNode ariNode;

                System.out.println("\n######### Start of recursive tests #############\n");

                expr =  "name = 'Station_1.Air Temperature'";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 1 failed.");

                expr =  "name = 'Station_1.Air Temperature' OR result > 4";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 3 failed.");

                expr =  "(name = 'Station_1.Air Temperature' OR result > 4.3210)";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 4 failed.");

                expr =  "name = 'Station_1.Air Temperature' OR (result > 30 AND result > 4)";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 4 failed.");

                expr =  "((name = 'Station_1.Air Temperature' OR (((result < 30) AND result > 4))))";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 5 failed.");

//                expr =  "(name = 'Station_1.Air Temperature' OR name = 'Station_2.Air Temperature') AND ((result < 30) AND result > 4)";
//                try {  // must fail
//                        logNode = new LogicalNode(expr);
//                        System.out.println("Test 6 failed.");
//                } catch (Exception ignored) {}

                expr =  "(result < 30 AND result < 4) OR name = 'Station_1.Air Temperature'";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 7 failed.");

                expr =  "result < 30 AND result < 4 OR name = 'Station_1.Air Temperature'";  // should be equal than the one above
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 8 failed.");


                System.out.println("\n######### Start of special operations #############\n");

//                System.out.println("\n######## Testing failures and exits #########\n");
//
//                expr =  "name = 'tricky_result_for this name' XOR result < 30 AND result > 4";
//                System.out.println(new LogicalNode(expr).getDegree());
//
//                expr =  "bad_Name = 'wrong keyword'"; // exit code 40
//                logNode = new LogicalNode(expr);
//
//                expr =  "TRUE"; // exit code 0
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "BAD_TRUE"; // exit code 40
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "name = 'tricky_result_for this name' XORG result < 30"; // exit code 45
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "result ~ 30"; // exit code 41
//                logNode = new LogicalNode(expr);
//
//                expr =  "result = 30'asdf'"; // no exit, but comparison, could also exit in sanity check
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "name = 'stranger's name'";  // exit code 44
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "30 = 'another beer'";  // exit code 40
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "result = 30asdf";  // exit code 52
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));
//
//                expr =  "result = 10 # pi";  // exit code 52
//                logNode = new LogicalNode(expr);
//                System.out.println(logNode.evaluate(jsonInput));


//                StreamQuery stream_parser = new StreamQuery(globalOptions);
//                System.out.println(stream_parser);
//                System.out.println(stream_parser.evaluate(jsonInput));

        }

        public static Properties globalOptions = new Properties();

}
