import sys
import os
import FeatureServer.Processing

import ConfigParser
# First, check explicit FS_CONFIG env var
if 'FS_CONFIG' in os.environ:
    cfgfiles = os.environ['FS_CONFIG'].split(",")

# Otherwise, make some guesses.
else:
    # Windows doesn't always do the 'working directory' check correctly.
    if sys.platform == 'win32':
        workingdir = os.path.abspath(os.path.join(os.getcwd(), os.path.dirname(sys.argv[0])))
        cfgfiles = (os.path.join(workingdir, "featureserver.cfg"), os.path.join(workingdir,"..","featureserver.cfg"))
    else:
        cfgfiles = ("featureserver.cfg", os.path.join("..", "featureserver.cfg"), "/etc/featureserver.cfg")




class Server (object):
    """The server manages the datasource list, and does the management of
       request input/output.  Handlers convert their specific internal
       representation to the parameters that dispatchRequest is expecting,
       then pass off to dispatchRequest. dispatchRequest turns the input
       parameters into a (content-type, response string) tuple, which the
       servers can then return to clients. It is possible to integrate
       FeatureServer into another content-serving framework like Django by
       simply creating your own datasources (passed to the init function)
       and calling the dispatchRequest method. The Server provides a classmethod
       to load datasources from a config file, which is the typical lightweight
       configuration method, but does use some amount of time at script startup.
       """

    def __init__ (self):
        self.datasources   = None
        self.metadata      = None
        self.processes     = None
        self.load(*cfgfiles)

    def loadFromSection (self, config, section, module_type, **objargs):
        type  = config.get(section, "type")
        module = __import__("FeatureServer.%s.%s" % (module_type, type), globals(), locals(), type)
        objclass = getattr(module, type)
        for opt in config.options(section):
            objargs[opt] = config.get(section, opt)
        if module_type is 'DataSource':
            return objclass(section, **objargs)
        else:
            return objclass(**objargs)


    def load (self, *files):
        """Class method on Service class to load datasources
           and metadata from a configuration file."""
        config = ConfigParser.ConfigParser()
        config.read(files)

        metadata = {}
        if config.has_section("metadata"):
            for key in config.options("metadata"):
                metadata[key] = config.get("metadata", key)

        processes = {}
        datasources = {}
        for section in config.sections():
            if section == "metadata": continue
            if section.startswith("process_"):
                try:
                    processes[section[8:]] = FeatureServer.Processing.loadFromSection(config, section)
                except Exception, E:
                    pass
            else:
                datasources[section] = self.loadFromSection(config, section, 'DataSource')

        self.metadata = metadata
        self.datasources = datasources
        self.processes = processes
