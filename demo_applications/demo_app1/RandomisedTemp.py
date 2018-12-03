#!/usr/bin/env python3

import random


class RandomisedTemp:
    def __init__(self):
        self.skew = 0
        self.curtemp = 50

    def get_temp(self):
        if self.curtemp > 70:
            self.skew = -0.1
        elif self.curtemp < 60:
            self.skew = 0.05
        self.curtemp += self.skew + random.normalvariate(mu=0, sigma=0.1)
        return self.curtemp
