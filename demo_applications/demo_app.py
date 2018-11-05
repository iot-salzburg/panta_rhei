#!/usr/bin/env python3
import os
import time
import random
import sys

from demo_applications.client.panta_rhei_client import PantaRheiClient

PANTA_RHEI_INSTANCES = "panta_rhei_mapping/instances.json"
PANTA_RHEI_SUBSCRIPTIONS = "panta_rhei_mapping/subscriptions.json"

client = PantaRheiClient()
client.register(instance_file=PANTA_RHEI_INSTANCES)
#client.subscribe(PANTA_RHEI_SUBSCRIPTIONS)



while False:
    demo_quantity0 = random.normalvariate(mu=0, sigma=1)
    demo_quantity1 = random.gammavariate(alpha=2, beta=2)

    client.send("demo_quantity0", demo_quantity0)
    client.send("demo_quantity1", demo_quantity1)

    print(demo_quantity0)
    print(demo_quantity1)

    demo_quantity3 = client.poll(datastream="demo_quantity3", timeout=0.1)
    print("Received new result for quantity 3: {}".format(demo_quantity3))
    time.sleep(5)
