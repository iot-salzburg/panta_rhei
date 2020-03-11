import fab_streams

stream = dict()
stream["SOURCE_SYSTEM"] = "is.iceland.iot4cps-wp5-WeatherService.Stations"
stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1"
stream["KAFKA_BOOTSTRAP_SERVERS"] = "172.16.98.186:9092"
stream["GOST_SERVER"] = "172.16.98.186:8082"
stream["FILTER_LOGIC"] = \
    "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30"


print(fab_streams.local_deploy(system_uuid="1234", stream_name="another-stream", stream=stream))
print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))
response1 = fab_streams.local_logs(system_uuid="1234", stream_name="another-stream")
response2 = fab_streams.local_stats(system_uuid="1234", stream_name="another-stream")
print(response2)
# print(fab_streams.local_down(system_uuid="1234", stream_name="another-stream"))
# print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))

