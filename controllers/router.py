import cherrypy

from model.server import Server


from lxml import etree
from cStringIO import StringIO

from collections import namedtuple

FSResponse = namedtuple('FSResponse', ['mime', 'data', 'headers', 'encoding'])

SERVICES = ['KML', 'GeoJSON','GeoRSS','HTML','OSM','WFS','SHP','CSV','GPX','OV2','SQLite','DXF']

def InServices(compval):
    for idx, val in enumerate(SERVICES):
        if val.lower() == str(compval).lower():
            return SERVICES[idx]
    return None

class Router(Server):


    def get(self, **kwargs):
        kwargs["method"] = "GET"
        response = self.process(kwargs)
        cherrypy.response.headers['Content-Type'] = response.mime
        return response.data

    def post(self, ws, **kwargs):
        message = {}
        if cherrypy.request.headers.get('Content-Type', None):
            if "application/xml" in cherrypy.request.headers.get('Content-Type').lower() \
                    or "text/xml" in cherrypy.request.headers.get('Content-Type').lower() \
                    or "application/atom+xml" in cherrypy.request.headers.get('Content-Type').lower():
                message["xml"] = cherrypy.request.body.read()
            if cherrypy.request.headers.get('Content-Type').lower() == "application/json":
                message["json"] =  message = cherrypy.request.json
        message["method"] = "POST"

        params = self.PostDataToParams(message)

        response = self.process(params)
        cherrypy.response.headers['Content-Type'] = response.mime
        return response.data

    def dummy(self, **kwargs):
        pass

    def process(self, params):
        params = self.normalizeParams(params)
        #===============================================================================
        # (reflection) dynamic load of format class e.g. WFS, KML, etc.
        # for supported format see package 'Service'
        #       -----------           -------
        #       | Request | <|------- | WFS |
        #       -----------           -------
        #===============================================================================
        try:
            service_type = InServices(params.get("service", "WFS"))
            if service_type is None:
                raise Exception("service can not be NULL")
            service_module = __import__("FeatureServer.Service.{_class}".format(_class=service_type), globals(), locals(), [service_type], -1 )
            service = getattr(service_module, service_type)
            request = service(self)
            request.workspace = params["ws"]
        except Exception as e:
            pass

        path_info = params["ws"]
        host = cherrypy.request.base
        post_data = None
        request_method = params["method"]
        try:
            #get stuff ready
            request.parse(params, path_info, host, post_data, "GET")

            thejob = request.actions[0].request.lower()
            if thejob == "getcapabilities":
                return self.getCapabilities(request, params)
            elif thejob == "describefeaturetype":
                return self.describeFeatureType(request, params)
            elif thejob == "getfeature":
                return self.getFeature(request, params)
            else:
                raise cherrypy.HTTPError("{_request} is unknown".format(_request=thejob))


        except Exception as e:
            pass


    #
    # GetCapabilities
    #
    def getCapabilities(self, request, params):
        version = params.get("version", "1.0.0")
        result = getattr(request, request.actions[0].request.lower())(version)
        return FSResponse(mime=result[0], data=result[1], headers=None, encoding='UTF-8')

    #
    # DescribeFeatureType
    #
    def describeFeatureType(self, request, params):
        version = params.get("version", "1.0.0")
        result = getattr(request, request.actions[0].request.lower())(version)
        return FSResponse(mime=result[0], data=result[1], headers=None, encoding='UTF-8')

    #
    # GetFeature
    #
    def getFeature(self, request, params):
        version = params.get("version", "1.0.0")
        datasource = self.datasources[request.datasources[0]]
        datasource.begin()
        if hasattr(datasource, 'nativebbox'):
            datasource.nativebbox = datasource.getBBOX()
        if hasattr(datasource, 'llbbox'):
            datasource.llbbox = datasource.getLLBBOX()

        #todo: figureout how this chains together
        for action in request.actions:
            method = getattr(datasource, action.method)
            result = method(action)

        mime, data, headers, encoding = request.encode(result)
        return FSResponse(mime, data, headers, encoding)




    #
    # Turn post data into the same params that get passed via get
    #
    def PostDataToParams(self, message):
        f = StringIO(message["xml"])
        tree = etree.parse(f)

        params = {'request': '', 'version': '1.0.0', 'ws': '', 'method': 'POST', 'service': ''}
        query = tree.xpath("//*[local-name() = 'GetCapabilities']")
        if len(query) > 0:
            attribs = query[0].attrib
            for key, value in attribs.items():
                if key.lower() == "service":
                    params["service"] = InServices(value)
                if key.lower() == "version":
                    params["version"] = value

            params["request"] = "getcapabilities"

            return params

        query = tree.xpath("//*[local-name() = 'DescribeFeatureType']")
        if len(query) > 0:
            attribs = query[0].attrib
            for key, value in attribs.items():
                if key.lower() == "service":
                    params["service"] = InServices(value)
                if key.lower() == "version":
                    params["version"] = value

            params["request"] = "describefeaturetype"

            return params

        query = tree.xpath("//*[local-name() = 'GetFeature']")
        if len(query) > 0:
            attribs = query[0].attrib
            for key, value in attribs.items():
                if key.lower() == "service":
                    params["service"] = InServices(value)

            subquery = tree.xpath("//*[local-name() = 'Query']")
            if len(subquery) > 0:
                attribs = subquery[0].attrib
                for key, value in attribs.items():
                    if key.lower() == "typename":
                        params["typename"] = value

                params["request"] = "getfeature"

                return params

        raise cherrypy.HTTPError("unknown post data")



    def normalizeParams(self, params):
        normparams = {}
        for key, value in params.items():
            if key.lower() == "typename" or key.lower() == "ws" or (type(value) is not str and type(value) is not unicode):
                normparams[key.lower()] = value
            else:
                normparams[key.lower()] = value.lower()
        return normparams