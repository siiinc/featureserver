"""
Simple class to allow and API endpoint to test if the web service is "alive"
"""

class Heartbeat(object):

    def heartbeat(self):
        return 'ok'