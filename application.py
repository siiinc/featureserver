## \mainpage
# Implementation of the workingsets service. This service manages the creation, update and delete of platform
# workingsets, setmembers and other core platform concepts.

import sys
import os
import cherrypy
from controllers.heartbeat import Heartbeat
from controllers.router import Router


SESSION_KEY = '_cp_workingsets'





# Initialize controllers
heartbeat = Heartbeat()
router = Router()





##Setup route-based dispatcher. NOTE: Routes 2.x does not seem to work - Routes 1.11 is required!
def setup_routes():
    rd = cherrypy.dispatch.RoutesDispatcher()
    rd.mapper.explicit = False

    rd.connect('heartbeat', '/heartbeat', controller=heartbeat, action='heartbeat', conditions=dict(method=['GET']))

    rd.connect('router_get', '/:ws', controller=router, action='get', conditions=dict(method=['GET']))
    rd.connect('router_post', '/:ws', controller=router, action='post', conditions=dict(method=['POST']))

    return rd



# Initialize the application server config
config = {
  'global': {
    'server.socket_host': "0.0.0.0",
    'server.socket_port': 8080
  },
  '/': {
    'request.dispatch': setup_routes()
  }
}


# Load config and mount the root object - note that because we use route-based dispatch the root is None.
cherrypy.config.update(config)
cherrypy.tree.mount(None, config=config)


# Elastic Beanstalk expects an application object:
application = cherrypy.tree


def run():
    """Start the server"""
    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    run()