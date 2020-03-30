package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;

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

//                expr =  "name == 'Station_1.Air Temperature'";  // must fail
//                try {
//                        logNode = new LogicalNode(expr);
//                        System.out.println("Test 2 failed.");
//                } catch (Exception ignored) {
//                        System.out.println("asdf");
//                }

                expr =  "name = 'Station_1.Air Temperature' OR result > 4";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 3 failed.");

                expr =  "(name = 'Station_1.Air Temperature' OR result > 4)";
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

                expr =  "result > 0 XOR name = 'Station_1.Air Temperature'";  // intro of XOR
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 9 failed.");

                expr =  "result = 0 XOR name = 'Station_1.Air Temperature'";  // intro of XOR
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 10 failed.");

                expr =  "name <> 'Station_1.Air Temperature'";  // intro of not equal, false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 11 failed.");

                expr =  "name <> 'Station_123.Air Temperature'";  // intro of not equal, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 12 failed.");


                expr =  "NOT result > 30";  // intro of not, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 13 failed.");

                expr =  "name <> 'Station_123.Air Temperature'";  // intro of not equal, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 14 failed.");

                expr =  " NOT NOT result > 30";  // intro of not, false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 15 failed.");

                expr =  "result < 30 AND NOT name = 'Station_123.Air Temperature'";  // intro of not, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 16 failed.");

                expr =  "NOT (result < 30 AND NOT name = 'Station_1.Air Temperature')";  // intro of not, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 17 failed.");

                expr =  "NOT NOT (result < 30 AND NOT NOT name = 'Station_1.Air Temperature')";  // intro of not, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 18 failed.");

                System.out.println("\n######### ordering and hierarchy #############\n");
                // ordering and hierarchy
                expr =  "result < 30 AND result > 4 AND name = 'Station_1.Air Temperature' ";  // true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 20 failed.");

                expr =  "result > 30 AND result > 4 AND name = 'Station_1.Air Temperature' ";  // false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 21 failed.");

                expr =  "result < 30 AND result > 4 AND name <> 'Station_1.Air Temperature' ";  // false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 23 failed.");

                expr =  "result > 30 AND result > 4 XOR name = 'Station_1.Air Temperature' ";  // true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 24 failed.");

                expr =  "name = 'Station_1.Air Temperature' XOR result > 30 AND result > 4";  // ordering, true
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 25 failed.");

                expr =  "result > 30 AND result > 4 OR name = 'Station_123.Air Temperature'";  // false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 26 failed.");

                expr =  "name = 'Station_123.Air Temperature' OR result > 30 AND result > 4";  // false
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 27 failed.");


                System.out.println("\n######## Testing arithmetic operations #########\n");


                expr = "2";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 2)
                        System.out.println("Test 30 failed.");

                expr = "2*3";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 6)
                        System.out.println("Test 31 failed.");

                expr = "2*3-1";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 5)
                        System.out.println("Test 32 failed.");

                expr = "2*3-1*100";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != -94)
                        System.out.println("Test 33 failed.");

                expr = "2*(3-1)*100";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 400)
                        System.out.println("Test 34 failed.");

                expr = "2*(3-1)^4";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 32)
                        System.out.println("Test 35 failed.");

                expr = "100 % 13";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 9)
                        System.out.println("Test 36 failed.");

                expr = "((100 ) % 13 ) ";
                if (new ArithmeticNode(expr).arithmeticEvaluate() != 9)
                        System.out.println("Test 37 failed.");

                expr = "2*3.1";  // there are rounding errors
                if (Math.abs(new ArithmeticNode(expr).arithmeticEvaluate() - 6.2) > 1E-6)
                        System.out.println("Test 38 failed: " + new ArithmeticNode(expr).arithmeticEvaluate());

                System.out.println("\n######## Combinations #########\n");

                expr =  "result < 3*10 AND result > 4-1";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 40 failed.");
                expr =  "result < 100 % 13 AND result > 0.4^10";
                if (new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 41 failed.");
                expr =  "100 > result AND result > 0.4^10";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 42 failed.");

                expr =  "result - 5 < 10";
                System.out.println(new LogicalNode(expr).evaluate(jsonInput));
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 43 failed.");

                expr =  "(result - 12.3)^2 = 0";
                if (!new LogicalNode(expr).evaluate(jsonInput))
                        System.out.println("Test 44 failed.");


                System.out.println("\n######## Testing the degree of the trees #########\n");

                expr = "2*(3-1)*100";
                if (new ArithmeticNode(expr).getDegree() != 3)
                        System.out.println("Test 51 failed, -> correct: " + new ArithmeticNode(expr).getDegree());

                expr =  "result < 10^10 % 13 AND result > 0.4^10";
                logNode = new LogicalNode(expr);
//                System.out.println(logNode.getDegree());
                if (logNode.getDegree() != 4)
                        System.out.println("Test 52 failed.");

//                StreamQuery stream_parser = new StreamQuery(globalOptions);
//                System.out.println(stream_parser);
//                System.out.println(stream_parser.evaluate(jsonInput));

        }

        public static Properties globalOptions = new Properties();

}
