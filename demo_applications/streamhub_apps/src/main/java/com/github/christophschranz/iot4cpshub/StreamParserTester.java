package com.github.christophschranz.iot4cpshub;

import com.google.gson.JsonObject;

import java.util.Properties;

public class StreamParserTester {

        public static void main(String[] args) {
        globalOptions.setProperty("STREAM_NAME", "test-stream");
        globalOptions.setProperty("SOURCE_SYSTEM", "is.iceland.iot4cps-wp5-WeatherService.Stations");
        globalOptions.setProperty("TARGET_SYSTEM", "cz.icecars.iot4cps-wp5-CarFleet.Car1");
        globalOptions.setProperty("KAFKA_BOOTSTRAP_SERVERS", "192.168.48.179:9092");
        globalOptions.setProperty("GOST_SERVER", "192.168.48.179:8082");
        globalOptions.setProperty("FILTER_LOGIC",
                "SELECT * FROM is.iceland.iot4cps-wp5-WeatherService.Stations " +
                        "WHERE name = 'Station_1.Air Temperature' AND value < 4");
        StreamParser strp = new StreamParser(globalOptions);
        System.out.println(strp);

        String expr = "name = 'Station_1.Air Temperature'";
        ComparisionNode anode = new ComparisionNode(expr);
        System.out.println(anode + "\n");

        expr =  "'Station_1.Air Temperature' = name";
        anode = new ComparisionNode(expr);
        System.out.println(anode + "\n");

        JsonObject jsonInput = new JsonObject();
        jsonInput.addProperty("name", "Station_1.Air Temperature");
        jsonInput.addProperty("result", 12.3);

        System.out.println(anode.isTrue(jsonInput));

}

        public static Properties globalOptions = new Properties();

}

