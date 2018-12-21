import sys
import json
import requests


class RegisterHelper:
    def __init__(self, logger, config):
        self.logger = logger
        self.config = config
        self.instances = dict()
        self.logger.warning("Created instance of RegisterHelper")

    def register(self, instance_file):

        self.logger.info("register: Loading instances")
        instances = self.load_instances(instance_file)
        self.logger.info("register: Loaded instances")

        gost_url = "http://" + self.config["gost_servers"]

        self.register_things(instances, gost_url)
        self.register_sensors(instances, gost_url)
        # self.register_observations(instances, gost_url)
        self.register_datastreams(instances, gost_url)

        self.logger.info("register: Successfully registered instances:")

        # Printing registered instances
        for category in list(self.instances.keys()):
            print(self.instances[category].items())
            items = [{"name": key, "@iot.id": value["@iot.id"]} for key, value
                     in list(self.instances[category].items())]
            self.logger.info("register: {}".format(items))

        return self.instances

    def load_instances(self, instance_file):
        """
        Gets the path to the instance_file,
        it loads the instances and write them back structured
        Checks the json for validity, "'" are not allowed, "''" must be used instead
        :param instance_file:
        :return: instances
        """
        with open(instance_file) as f:
            content = f.read()
            instances = json.loads(content)

            # Check the file for validity
            interquotes = [interquote for interquote in content.split("\'")[1::2] if interquote != ""]
            del content
            if len(interquotes) > 0:
                self.logger.error("There are single quotes in the instance file near: {}".format(
                    str(interquotes)[:100]))
                self.logger.info("Please replace the single quotes with duplicate single quotes, "
                                 "e.g. It''s time to party.")
                sys.exit()
        # Make structure pretty
        with open(instance_file, "w") as f:
            f.write(json.dumps(instances, indent=2))

        return instances

    def register_things(self, instances, gost_url):
        """
        Opens the Things of the instance file
        create requests
        If they exist: make patches
        Else: make posts and create the instance new
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :param gost_url. URL of the gost server
        :return:
        """

        # Register Things. Patch or post
        self.logger.info("register: Register Things")
        gost_things = requests.get(gost_url + "/v1.0/Things").json()
        gost_thing_list = [thing["name"] for thing in gost_things["value"]]
        for thing in instances["Things"].keys():
            name = instances["Things"][thing]["name"]
            self.logger.info("register: Thing: {}, GOST name: {}".format(thing, name))
            # PATCH thing
            if name in gost_thing_list:
                idx = [gost_thing for gost_thing in gost_things["value"] if name == gost_thing["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Things({})".format(idx)
                self.logger.debug("register: Make a patch of: {}".format(json.dumps(instances["Things"][thing]["name"],
                                                                                    indent=2)))
                res = requests.patch(uri, json=instances["Things"][thing])
            # POST thing
            else:
                self.logger.debug("register: Make a post of: {}".format(json.dumps(instances["Things"][thing]["name"],
                                                                                   indent=2)))
                uri = gost_url + "/v1.0/Things"
                res = requests.post(uri, json=instances["Things"][thing])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Thing: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Things"][thing] = res.json()

            else:
                self.logger.warning(
                    "register: Problems in upserting Things on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, res.status_code, json.dumps(res.json(), indent=2)))

        self.instances["Things"] = instances["Things"]

    def register_sensors(self, instances, gost_url):
        """
        Opens the Sensors of the instance file
        create requests
        If they exist: make patches
        Else: make posts and create the instance new
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :param gost_url. URL of the gost server
        :return:
        """
        # Register Sensors. Patch or post
        self.logger.info("register: Register Sensors")
        gost_sensors = requests.get(gost_url + "/v1.0/Sensors").json()
        gost_sensor_list = [sensor["name"] for sensor in gost_sensors["value"]]
        for sensor in instances["Sensors"].keys():
            name = instances["Sensors"][sensor]["name"]
            self.logger.info("register: Sensor: {}, GOST name: {}".format(sensor, name))
            status_max = 0
            res = None
            # PATCH sensor
            if name in gost_sensor_list:
                idx = [gost_sensor for gost_sensor in gost_sensors["value"]
                       if name == gost_sensor["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Sensors({})".format(idx)
                # Sensors can only be patched line by line
                for arg in list(instances["Sensors"][sensor]):
                    body = dict({arg: instances["Sensors"][sensor][arg]})
                    res = requests.patch(uri, json=body)
                    status_max = max(res.status_code, status_max)  # Show the maximal status

            # POST sensor
            else:
                self.logger.debug("Make a post of: {}".format(json.dumps(instances["Sensors"][sensor]["name"],
                                                                         indent=2)))
                uri = gost_url + "/v1.0/Sensors"
                res = requests.post(uri, json=instances["Sensors"][sensor])
                status_max = max(res.status_code, status_max)
            # Test if everything worked
            if status_max in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Sensors: {} with the URI: {} and status code: {}".format(
                        name, uri, status_max))
                instances["Sensors"][sensor] = res.json()
            else:
                self.logger.warning(
                    "register: Problems to upsert Sensors on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, status_max, json.dumps(res.json(), indent=2)))

        self.instances["Sensors"] = instances["Sensors"]

    def register_datastreams(self, instances, gost_url):
        """
        Opens the Datastreams with observed properties of the instance file
        create requests
        If they exist: make patches
        Else: make posts and create the instance new
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :param gost_url. URL of the gost server
        :return:
        """
        # TODO Register Observation property extra, make an own class to register all instances
        # Register Datastreams with observation. Patch or post
        self.logger.info("register: Register Datastreams")
        gost_datastreams = requests.get(gost_url + "/v1.0/Datastreams").json()
        gost_datastream_list = [datastream["name"] for datastream in gost_datastreams["value"]]
        for datastream in instances["Datastreams"].keys():
            name = instances["Datastreams"][datastream]["name"]
            self.logger.info("register: Datastream: {}, GOST name: {}".format(datastream, name))

            dedicated_thing = instances["Datastreams"][datastream]["Thing"]
            dedicated_sensor = instances["Datastreams"][datastream]["Sensor"]

            instances["Datastreams"][datastream]["Thing"] = dict({
                "@iot.id": instances["Things"][dedicated_thing]["@iot.id"]})
            instances["Datastreams"][datastream]["Sensor"] = dict({
                "@iot.id": instances["Sensors"][dedicated_sensor]["@iot.id"]})

            # Deep patch is not supported, no Thing, Sensor or Observed property
            # PATCH thing
            if name in gost_datastream_list:
                idx = [gost_datastreams for gost_datastreams in gost_datastreams["value"]
                       if name == gost_datastreams["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Datastreams({})".format(idx)
                self.logger.info("register: Make a patch of: {}".format(
                    json.dumps(instances["Datastreams"][datastream]["name"], indent=2)))

                instances["Datastreams"][datastream].pop("Thing", None)
                instances["Datastreams"][datastream].pop("Sensor", None)
                instances["Datastreams"][datastream].pop("ObservedProperty", None)
                res = requests.patch(uri, json=instances["Datastreams"][datastream])
            # POST datastream
            else:
                self.logger.info("register: Make a post of: {}".format(json.dumps(
                    instances["Datastreams"][datastream]["name"], indent=2)))
                uri = gost_url + "/v1.0/Datastreams"
                res = requests.post(uri, json=instances["Datastreams"][datastream])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Datastreams: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Datastreams"][datastream] = res.json()
            else:
                self.logger.warning(
                    "register: Problems to upsert Datastreams on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, res.status_code, json.dumps(res.json(), indent=2)))
                print(json.dumps(instances["Datastreams"][datastream]))

        self.instances["Datastreams"] = instances["Datastreams"]
