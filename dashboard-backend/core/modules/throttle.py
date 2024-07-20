from rest_framework.throttling import AnonRateThrottle
from rest_framework.exceptions import Throttled


class AnonymousThrottle(AnonRateThrottle):
    rate = "3/day"
    message = "Too many request, please try again later"

    def get_rate(self):
        return self.rate

    def wait(self):
        raise Throttled(None, self.message)




