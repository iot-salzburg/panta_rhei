# StreamAppEngine

## Deployment Notes

### Testing the filter logic

Testing the stream engine with `NodeTester.java`. 
Many filtering examples are in the code.


### Testing with Streams

In `StreamAppEngine` an the environment variables are passed.
This are the variables:
```
STREAM_NAME="test-stream"
SOURCE_SYSTEM=is.iceland.iot4cps-wp5-WeatherService.Stations
TARGET_SYSTEM=cz.icecars.iot4cps-wp5-CarFleet.Car1
KAFKA_BOOTSTRAP_SERVERS=192.168.48.179:9092
GOST_SERVER=192.168.48.179:8082;
FILTER_LOGIC="SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30\;"
```

Using them, the Application can be started.


### Deploying the jar file

To build a *jar* file, open the **Maven** sidebar and click 
`clean` and `install`. Both should exit with the info `BUILD SUCCESS`.

Afterwards, the **jar** file can be executed using:
```bash
java -jar target/streamApp-1.1-jar-with-dependencies.jar --STREAM_NAME test-jar --SOURCE_SYSTEM is.iceland.iot4cps-wp5-WeatherService.Stations --TARGET_SYSTEM cz.icecars.iot4cps-wp5-CarFleet.Car1 --KAFKA_BOOTSTRAP_SERVERS 192.168.48.179:9092 --GOST_SERVER 192.168.48.179:8082 --FILTER_LOGIC "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30;"
```

### Testing via the GUI

This step requires a running platform as explained in the `server` directory.
Then, copy the jar file from `demo_applications/stream_apps/target` to `server/views`.
Restart the platform and go to *streams* and click on *start stream*.

