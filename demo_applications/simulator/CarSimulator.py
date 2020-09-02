#!/usr/bin/env python3
"""
This class has the purpose to simulate a car's movement on a track in Salzburg, on which temperature data
and breaking events occur. This class is aimed to be used by the car instances within the CarFleet
demonstration company.
"""
import math
import os
import sys
import time
import json
import random
import logging

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
# noinspection PyUnresolvedReferences
from SimulateTemperatures import SimulateTemperatures

# Tracks are downloaded from https://maps.openrouteservice.org/
TRACK_MAP = {1: "openroute_SRFG-round.json", 2: "openroute_Mirabellplatz-round.json", 3: "openroute_Muelln-round.json"}
UPDATE_THRESHOLD = 0.001  # threshold, update positions if this is surpassed in coordinate getter.


class CarSimulator:
    def __init__(self, track_id=-1, time_factor=100.0, speed=30, cautiousness=1,
                 temp_day_amplitude=5, temp_year_amplitude=-5, temp_average=2.5, seed=None):
        # Store start_time
        self.start_time = time.time()
        self.last_update = 0
        self.last_moved = 0
        self.track = dict()
        self.track_id = track_id
        self.track_idx = 0
        self.old_step = 0
        self.speed = speed
        self.time_factor = time_factor
        self.gps_latitude = 0
        self.gps_longitude = 0
        self.gps_attitude = 0
        if cautiousness < 0.1:
            raise Exception("The cautiousness must not undercut 0.1.")
        self.cautiousness = cautiousness
        self.last_acceleration = self.start_time
        if seed is not None:
            random.seed(seed)

        logging.basicConfig(level=logging.WARNING)
        self.logger = logging.getLogger("CarSimulator")
        self.logger.setLevel(logging.INFO)

        self.logger.info("Created instance of class CarSimulator.")
        self.temp = SimulateTemperatures(time_factor=time_factor, day_amplitude=temp_day_amplitude,
                                         year_amplitude=temp_year_amplitude, average=temp_average, seed=seed)

        self.get_start_positions()

    def get_start_positions(self):
        # If track_id is not set, use a random track
        if self.track_id == -1:
            self.track_id = random.sample(TRACK_MAP.keys(), k=1)[0]

        # raise an error if the track_id is not in the TRACK_MAP
        elif self.track_id not in TRACK_MAP.keys():
            raise KeyError("The given track with id '{}' doesn't exist. Choose one of: '{}'".format(
                self.track_id, json.dumps(TRACK_MAP)))

        # Load the track and store as dictionary, check if it contains enough vertices
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),  TRACK_MAP[self.track_id])) as track_file:
            self.track = json.loads(track_file.read().encode("utf-8"))
            if self.track.get("geometry") is None:
                raise Exception("The track with name '{}' can't be loaded.".format(TRACK_MAP[self.track_id]))
            if len(self.track.get("geometry")) < 10:
                raise Exception("The track with name '{}' has not enough vertices.".format(TRACK_MAP[self.track_id]))

        self.logger.info("Driving on track: '{}' with a speed of {} m/s.".format(TRACK_MAP[self.track_id], self.speed))
        # Load the starting positions
        self.update_positions()

    def update_positions(self, n=0):
        if n > 10:
            raise RecursionError("defined maximum recursion depth exceeded")
        self.last_update = time.time()
        self.logger.debug("Passed track index: {}".format(self.track_idx))  # The first 3 entries (2) are 0

        if self.last_moved == 0:  # zero is the initial starting point
            # Update the GPS positions
            self.gps_latitude = self.track.get("geometry")[self.track_idx][0]
            self.gps_longitude = self.track.get("geometry")[self.track_idx][1]
            self.gps_attitude = self.track.get("geometry")[self.track_idx][2]
            self.last_moved = time.time()

        # Interpolate the positions
        else:  # if it is not the initial starting point
            delta_time = time.time() - self.last_moved  # delta time is in seconds
            step = delta_time * self.speed / 3.6 * self.time_factor + self.old_step  # step is in metres
            self.logger.debug("Step to go: {} m".format(round(step, 2)))
            next_vertex_dist = self.get_next_vertex_dist()
            self.logger.debug("next_vertex_dist: {} m".format(round(next_vertex_dist, 2)))
            if step < 1:
                self.logger.debug("Update not done, the car has moved less than 1 meter.")
                return None

            # iterate to the index after which there is the new position
            while step >= next_vertex_dist and self.track_idx < len(self.track.get("geometry")) - 2:
                step -= next_vertex_dist
                self.track_idx += 1
                next_vertex_dist = self.get_next_vertex_dist()

            # Overflow of indices, track should begin at index 0
            if self.track_idx >= len(self.track.get("geometry"))-2:
                self.logger.debug("Overflow occurred, restart at index 0.")
                self.track_idx = 0
                self.old_step = 0
                # self.last_moved = time.time()
                self.update_positions(n=n+1)
            else:
                # Now interpolate latitude, longitude and attitude between self.track_idx and self.track_idx+1
                self.old_step = step
                dist_ratio = self.old_step / next_vertex_dist
                self.gps_latitude = self.interpolate_position(dist_ratio, 0)
                self.gps_longitude = self.interpolate_position(dist_ratio, 1)
                self.gps_attitude = self.interpolate_position(dist_ratio, 2)
                self.last_moved = time.time()

    def get_next_vertex_dist(self):
        # Calculate the distance between two vertices
        lat0 = self.track.get("geometry")[self.track_idx][0]
        lon0 = self.track.get("geometry")[self.track_idx][1]
        lat1 = self.track.get("geometry")[self.track_idx+1][0]
        lon1 = self.track.get("geometry")[self.track_idx+1][1]

        # Calculate the distances in meters based on latitude and longitude. (only correct for not to big edges!)
        dx = 40075*1000/360 * math.cos((lat1-lat0)/2*math.pi/180) * (lon1-lon0)
        dy = 40075*1000/360 * (lat1-lat0)
        # dist = 40075*1000 / 2 / math.pi  # Calculate via the "Seitenkosinussatz" (not needed)
        # dist *= acos(sin(lat1*pi/180)*sin(lat2*pi/180) + cos(lat1*pi/180)*cos(lat2*pi/180)*cos((lon2-lon1)*pi/180))
        return (dx**2 + dy**2)**0.5

    def interpolate_position(self, dist_ratio, k):
        # Interpolate linearly between the coordinates with index self.track_idx and self.track_idx+1
        # for all three coordinates noted by k.
        position = self.track.get("geometry")[self.track_idx][k] + dist_ratio * \
                   (self.track.get("geometry")[self.track_idx + 1][k] - self.track.get("geometry")[self.track_idx][k])
        return position

    def get_latitude(self):
        if time.time() - self.last_update > UPDATE_THRESHOLD:
            self.logger.debug("The latitude might be deprecated, updating positions.")
            self.update_positions()
        return round(self.gps_latitude, 6)

    def get_longitude(self):
        if time.time() - self.last_update > UPDATE_THRESHOLD:
            self.logger.debug("The longitude might be deprecated, updating positions.")
            self.update_positions()
        return round(self.gps_longitude, 6)

    def get_attitude(self):
        if time.time() - self.last_update > UPDATE_THRESHOLD:
            self.logger.debug("The attitude might be deprecated, updating positions.")
            self.update_positions()
        return round(self.gps_attitude, 6)

    def get_acceleration(self):
        delta_time = int(0.1*self.time_factor * (time.time() - self.last_acceleration))
        if delta_time == 0:
            self.logger.debug("delta_time in get_acceleration is very small.")
            return round(min([random.random() for _ in range(5)]), 3)
        # A breaking event per second is drawn from an exponential distribution f(x)=l*e^-(lx), as it is memoryless.
        # The temperature is normalized with 4° and a=0.1
        influences = 3/(1+math.exp(0.1*(4-self.temp.get_temp())))
        # The position should have an effect, multiply with 100 to see an effect within a city
        influences += math.sin(100*self.get_latitude()) + math.sin(100*self.get_longitude())
        accelerations = [random.expovariate(self.cautiousness * (5 + influences))
                         for _ in range(delta_time)]
        self.last_acceleration = int(time.time())
        return round(max(accelerations), 3)


if __name__ == "__main__":
    print("Creating an instance of a simulated car.")
    car = CarSimulator(track_id=3, time_factor=10, speed=30, cautiousness=1,
                       temp_day_amplitude=5, temp_year_amplitude=-5, temp_average=2.5, seed=0)

    while True:
        car.update_positions()
        print("The car is at [{}, {}], measures the temperature: {} °C and had a highest acceleration of {} m/s²".
              format(car.get_latitude(), car.get_longitude(), car.temp.get_temp(), car.get_acceleration()))
        time.sleep(1)
