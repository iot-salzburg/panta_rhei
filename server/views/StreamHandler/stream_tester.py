import sys
import time

import fab_streams

stream = dict()
stream["KAFKA_BOOTSTRAP_SERVERS"] = "127.0.0.1:9094"
stream["GOST_SERVER"] = "127.0.0.1:8082"


print("Testing a multi-source stream app with default filter logic")
stream["SOURCE_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1,cz.icecars.iot4cps-wp5-CarFleet.Car2"
stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car2"
stream["FILTER_LOGIC"] = None

print(fab_streams.local_deploy_multi(system_uuid="1234", stream_name="another-stream", stream=stream))
time.sleep(5)
print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))
response1 = fab_streams.local_logs(system_uuid="1234", stream_name="another-stream")
response2 = fab_streams.local_stats(system_uuid="1234", stream_name="another-stream")
print(response1)
print(response2)
print(fab_streams.local_down(system_uuid="1234", stream_name="another-stream"))
print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))

sys.exit(12)


print("Testing a single-source stream app")
stream["SOURCE_SYSTEM"] = "is.iceland.iot4cps-wp5-WeatherService.Stations"
stream["TARGET_SYSTEM"] = "cz.icecars.iot4cps-wp5-CarFleet.Car1"
stream["FILTER_LOGIC"] = \
    "SELECT * FROM * WHERE (name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_1.Air Temperature' OR name = 'is.iceland.iot4cps-wp5-WeatherService.Stations.Station_2.Air Temperature') AND result < 30"

print(fab_streams.local_deploy(system_uuid="1234", stream_name="another-stream", stream=stream))
time.sleep(5)
print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))
response1 = fab_streams.local_logs(system_uuid="1234", stream_name="another-stream")
response2 = fab_streams.local_stats(system_uuid="1234", stream_name="another-stream")
print(response1)
print(response2)
print(fab_streams.local_down(system_uuid="1234", stream_name="another-stream"))
print(fab_streams.local_is_deployed(system_uuid="1234", stream_name="another-stream"))

