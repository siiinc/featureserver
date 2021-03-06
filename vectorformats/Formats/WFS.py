from vectorformats.Formats.Format import Format
import re, xml.dom.minidom as m
from lxml import etree
from xml.sax.saxutils import escape
from cStringIO import StringIO

class WFS(Format):
    """WFS-like GML writer."""
    layername = "layer"
    namespaces = {'fs' : 'http://featureserver.org/fs',
                  'wfs' : 'http://www.opengis.net/wfs',
                  'ogc' : 'http://www.opengis.net/ogc',
                  'xsd' : 'http://www.w3.org/2001/XMLSchema',
                  'gml' : 'http://www.opengis.net/gml',
                  'xsi' : 'http://www.w3.org/2001/XMLSchema-instance'}

    def encode(self, features, **kwargs):
        wfsstr = StringIO()
        wfsstr.write('<?xml version="1.0" ?><wfs:FeatureCollection xmlns:fs="http://featureserver.org/fs" xmlns:wfs="http://www.opengis.net/wfs" xmlns:gml="http://www.opengis.net/gml" xmlns:ogc="http://www.opengis.net/ogc" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.opengis.net/wfs http://schemas.opengeospatial.net//wfs/1.0.0/WFS-basic.xsd">')
        for feature in features:
            self.encode_feature(wfsstr, feature)
        wfsstr.write("</wfs:FeatureCollection>")

        return wfsstr.getvalue()

    def encode_feature(self, wfsstr, feature):
        layername = re.sub(r'\W', '_', self.layername)

        attr_fields = []
        for key, value in feature.properties.items():
            #key = re.sub(r'\W', '_', key)
            attr_value = value
            if hasattr(attr_value,"replace"):
                attr_value = attr_value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if isinstance(attr_value, str):
                attr_value = unicode(attr_value, "utf-8")
            attr_fields.append( "<fs:%s>%s</fs:%s>" % (key, attr_value, key) )


        wfsstr.write("<gml:featureMember gml:id=\"%s\"><fs:%s fid=\"%s\">" % (str(feature.id), layername, str(feature.id)))

        if hasattr(feature, "geometry_attr"):
            wfsstr.write("<fs:%s>" % feature.geometry_attr)
            self.geometry_to_gml(wfsstr,feature.geometry, feature.srs)
            wfsstr.write("</fs:%s>" % feature.geometry_attr)
        else:
            self.geometry_to_gml(wfsstr, feature.geometry, feature.srs)

        wfsstr.write("%s</fs:%s></gml:featureMember>" % ("\n".join(attr_fields), layername))

    def geometry_to_gml(self, wfsstr, geometry, srs):
        """
        >>> w = WFS()
        >>> print w.geometry_to_gml({'type':'Point', 'coordinates':[1.0,2.0]})
        <gml:Point><gml:coordinates>1.0,2.0</gml:coordinates></gml:Point>
        >>> w.geometry_to_gml({'type':'LineString', 'coordinates':[[1.0,2.0],[2.0,1.0]]})
        '<gml:LineString><gml:coordinates>1.0,2.0 2.0,1.0</gml:coordinates></gml:LineString>'
        """

        srs_code = srs

        if "EPSG" not in str(srs):
            srs = "EPSG:" + str(srs)

        if "Point" == geometry['type']:
            coords = ",".join(map(str, geometry['coordinates']))
            wfsstr.write( "<gml:Point srsName=\"%s\"><gml:coordinates decimal=\".\" cs=\",\" ts=\" \">%s</gml:coordinates></gml:Point>" % (str(srs), coords) )


        elif "MultiPoint" == geometry['type']:

            wfsstr.write('<gml:MultiPoint srsName="http://www.opengis.net/gml/srs/epsg.xml#{_srs}">'.format(_srs=str(srs_code)))
            member = '<gml:pointMember><gml:Point><gml:coordinates xmlns:gml="http://www.opengis.net/gml" decimal=\".\" cs=\",\" ts=\" \">{_coords}</gml:coordinates></gml:Point></gml:pointMember>'

            for geom in geometry['coordinates']:
                coords = ",".join(map(str, geom))
                wfsstr.write(member.format(_coords=coords))

            wfsstr.write('</gml:MultiPoint>')


        elif "LineString" == geometry['type']:
            coords = " ".join(",".join(map(str, coord)) for coord in geometry['coordinates'])
            tstr = "<gml:LineString><gml:coordinates decimal=\".\" cs=\",\" ts=\" \" srsName=\"%s\">%s</gml:coordinates></gml:LineString>" % (str(srs), coords)
            wfsstr.write(tstr)


        elif "MultiLineString" == geometry['type']:
            wfsstr.write('<gml:MultiLineString srsName="http://www.opengis.net/gml/srs/epsg.xml#{_srs}">'.format(_srs=str(srs_code)))
            member = '<gml:lineStringMember><gml:LineString><gml:coordinates xmlns:gml="http://www.opengis.net/gml" decimal=\".\" cs=\",\" ts=\" \">{_coords}</gml:coordinates></gml:LineString></gml:lineStringMember>'

            for geom in geometry['coordinates']:
                coords = " ".join(map(lambda x: ",".join(map(str, x)), geom))
                wfsstr.write(member.format(_coords=coords))

            wfsstr.write('</gml:MultiLineString>')



        elif "Polygon" == geometry['type']:
            coords = " ".join(map(lambda x: ",".join(map(str, x)), geometry['coordinates'][0]))
            #out = """
            #    <gml:exterior>
            #        <gml:LinearRing>
            #            <gml:coordinates decimal=\".\" cs=\",\" ts=\" \">%s</gml:coordinates>
            #        </gml:LinearRing>
            #    </gml:exterior>
            #""" % coords
            out = """
                <gml:exterior>
                    <gml:LinearRing srsDimension="2">
                        <gml:coordinates>%s</gml:coordinates>
                    </gml:LinearRing>
                </gml:exterior>
            """ % coords

            inner_rings = []
            for inner_ring in geometry['coordinates'][1:]:
                coords = " ".join(map(lambda x: ",".join(map(str, x)), inner_ring))
                #inner_rings.append("""
                #    <gml:interior>
                #        <gml:LinearRing>
                #            <gml:coordinates decimal=\".\" cs=\",\" ts=\" \">%s</gml:coordinates>
                #        </gml:LinearRing>
                #    </gml:interior>
                #""" % coords)
                inner_rings.append("""
                    <gml:interior>
                        <gml:LinearRing srsDimension="2">
                            <gml:coordinates>%s</gml:coordinates>
                        </gml:LinearRing>
                    </gml:interior>
                """ % coords)

            wfsstr.write("""
                            <gml:Polygon srsName="%s">
                                %s %s
                            </gml:Polygon>""" % (srs, out, "".join(inner_rings)))

        elif "MultiPolygon" == geometry['type']:
            wfsstr.write('<gml:MultiPolygon srsName="http://www.opengis.net/gml/srs/epsg.xml#{_srs}">'.format(_srs=str(srs_code)))
            member = '<gml:polygonMember><gml:Polygon><gml:outerBoundaryIs><gml:LinearRing><gml:coordinates xmlns:gml="http://www.opengis.net/gml" decimal=\".\" cs=\",\" ts=\" \">{_coords}</gml:coordinates></gml:LinearRing></gml:outerBoundaryIs></gml:Polygon></gml:polygonMember>'

            for geom in geometry['coordinates']:
                coords = " ".join(map(lambda x: ",".join(map(str, x)), geom))
                wfsstr.write(member.format(_coords=coords))

            wfsstr.write('</gml:MultiPolygon>')


        else:
            raise Exception("Could not convert geometry of type %s." % geometry['type'])


    def encode_exception_report(self, exceptionReport):
        results = ["""<?xml version="1.0" encoding="UTF-8"?>
        <ExceptionReport xmlns="http://www.opengis.net/ows/1.1"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.opengis.net/ows/1.1 owsExceptionReport.xsd"
        version="1.0.0"
        xml:lang="en">
        """]
        for exception in exceptionReport:
            results.append("<Exception exceptionCode=\"%s\" locator=\"%s\" layer=\"%s\"><ExceptionText>%s</ExceptionText><ExceptionDump>%s</ExceptionDump></Exception>" % (exception.code, exception.locator, exception.layer, exception.message, exception.dump))
        results.append("""</ExceptionReport>""")
        return "\n".join(results)

    def encode_transaction(self, response, **kwargs):
        failedCount = 0

        summary = response.getSummary()
        result = """<?xml version="1.0" encoding="UTF-8"?>
        <wfs:TransactionResponse version="1.1.0"
            xsi:schemaLocation='http://www.opengis.net/wfs http://schemas.opengis.net/wfs/1.0.0/WFS-transaction.xsd'
            xmlns:og="http://opengeo.org"
            xmlns:ogc="http://www.opengis.net/ogc"
            xmlns:tiger="http://www.census.gov"
            xmlns:cite="http://www.opengeospatial.net/cite"
            xmlns:nurc="http://www.nurc.nato.int"
            xmlns:sde="http://geoserver.sf.net"
            xmlns:analytics="http://opengeo.org/analytics"
            xmlns:wfs="http://www.opengis.net/wfs"
            xmlns:topp="http://www.openplans.org/topp"
            xmlns:it.geosolutions="http://www.geo-solutions.it"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:sf="http://www.openplans.org/spearfish"
            xmlns:ows="http://www.opengis.net/ows"
            xmlns:gml="http://www.opengis.net/gml"
            xmlns:za="http://opengeo.org/za"
            xmlns:xlink="http://www.w3.org/1999/xlink"
            xmlns:tike="http://opengeo.org/#tike">
                <wfs:TransactionSummary>
                    <wfs:totalInserted>%s</wfs:totalInserted>
                    <wfs:totalUpdated>%s</wfs:totalUpdated>
                    <wfs:totalDeleted>%s</wfs:totalDeleted>
                    <wfs:totalReplaced>%s</wfs:totalReplaced>
                </wfs:TransactionSummary>
            <wfs:TransactionResults/> """ % (str(summary.getTotalInserted()), str(summary.getTotalUpdated()), str(summary.getTotalDeleted()), str(summary.getTotalReplaced()))

        insertResult = response.getInsertResults()
        result += "<wfs:InsertResults>"
        for insert in insertResult:
            result += """<wfs:Feature handle="%s">
                    <ogc:ResourceId fid="%s"/>
                </wfs:Feature>""" % (str(insert.getHandle()), str(insert.getResourceId()))
            if len(insert.getHandle()) > 0:
                failedCount += 1
        result += """</wfs:InsertResults>"""

        updateResult = response.getUpdateResults()
        result += "<wfs:UpdateResults>"
        for update in updateResult:
            result += """<wfs:Feature handle="%s">
                    <ogc:ResourceId fid="%s"/>
                </wfs:Feature>""" % (str(update.getHandle()), str(update.getResourceId()))
            if len(update.getHandle()) > 0:
                failedCount += 1

        result += """</wfs:UpdateResults>"""

        replaceResult = response.getReplaceResults()
        result += "<wfs:ReplaceResults>"
        for replace in replaceResult:
            result += """<wfs:Feature handle="%s">
                    <ogc:ResourceId fid="%s"/>
                </wfs:Feature>""" % (str(replace.getHandle()), str(replace.getResourceId()))
            if len(replace.getHandle()) > 0:
                failedCount += 1
        result += """</wfs:ReplaceResults>"""


        deleteResult = response.getDeleteResults()
        result += "<wfs:DeleteResults>"
        for delete in deleteResult:
            result += """<wfs:Feature handle="%s">
                <ogc:ResourceId fid="%s"/>
                </wfs:Feature>""" % (str(delete.getHandle()), str(delete.getResourceId()))
            if len(delete.getHandle()) > 0:
                failedCount += 1
        result += """</wfs:DeleteResults>"""


        result += """<wfs:TransactionResult>
                        <wfs:Status> """

        if (len(insertResult) + len(updateResult) + len(replaceResult)) == failedCount:
            result += "<wfs:FAILED/>"
        elif (len(insertResult) + len(updateResult) + len(replaceResult)) > failedCount and failedCount > 0:
            result += "<wfs:PARTIAL/>"
        else:
            result += "<wfs:SUCCESS/>"


        result += """</wfs:Status>
                </wfs:TransactionResult>"""


        result += """</wfs:TransactionResponse>"""

        return result

    def getcapabilities(self):
        tree = etree.parse("resources/wfs-capabilities.xml")
        root = tree.getroot()
        elements = root.xpath("wfs:Capability/wfs:Request/wfs:GetCapabilities/wfs:DCPType/wfs:HTTP", namespaces = self.namespaces)
        if len(elements) > 0:
            for element in elements:
                for http in element:
                    http.set('onlineResource', self.host + '?' + 'Request=GetCapabilities')

        elements = root.xpath("wfs:Capability/wfs:Request/wfs:DescribeFeatureType/wfs:DCPType/wfs:HTTP", namespaces = self.namespaces)
        if len(elements) > 0:
            for element in elements:
                for http in element:
                    http.set('onlineResource', self.host + '?' + 'Request=DescribeFeatureType')

        elements = root.xpath("wfs:Capability/wfs:Request/wfs:GetFeature/wfs:DCPType/wfs:HTTP", namespaces = self.namespaces)
        if len(elements) > 0:
            for element in elements:
                for http in element:
                    http.set('onlineResource', self.host + '?' + 'Request=GetFeature')

        elements = root.xpath("wfs:Capability/wfs:Request/wfs:Transaction/wfs:DCPType/wfs:HTTP", namespaces = self.namespaces)
        if len(elements) > 0:
            for element in elements:
                for http in element:
                    http.set('onlineResource', self.host + '?' + 'Request=Transaction')


        layers = self.getlayers()
        featureList = root.xpath("wfs:FeatureTypeList", namespaces = self.namespaces)
        if len(featureList) > 0 and len(layers) > 0:
            for layer in layers:
                featureList[0].append(layer)

        return etree.tostring(tree, pretty_print=True)

    def getlayers(self):
        ''' '''
        featureList = etree.Element('{http://www.opengis.net/wfs}FeatureTypeList')
        operations = etree.Element('{http://www.opengis.net/wfs}Operations')
        operations.append(etree.Element('{http://www.opengis.net/wfs}Query'))
        featureList.append(operations)

        for layer in self.layers:
            type = etree.Element('{http://www.opengis.net/wfs}FeatureType')
            name = etree.Element('{http://www.opengis.net/wfs}Name')
            name.text = layer
            type.append(name)

            title = etree.Element('{http://www.opengis.net/wfs}Title')
            if hasattr(self.datasources[layer], 'title'):
                title.text = self.datasources[layer].title
            elif hasattr(self.datasources[layer], 'name'):
                title.text = self.datasources[layer].name
            type.append(title)

            abstract = etree.Element('{http://www.opengis.net/wfs}Abstract')
            if hasattr(self.datasources[layer], 'abstract'):
                abstract.text = self.datasources[layer].abstract
            type.append(abstract)

            keywords = etree.Element('{http://www.opengis.net/wfs}Keywords')
            if hasattr(self.datasources[layer], 'keywords'):
                keywords.text = self.datasources[layer].abstract
            else:
                keywords.text = "{_name}, features".format(_name=self.datasources[layer].name)
            type.append(abstract)


            srs = etree.Element('{http://www.opengis.net/wfs}SRS')
            if hasattr(self.datasources[layer], 'srid_out') and self.datasources[layer].srid_out is not None:
                srs.text = 'EPSG:' + str(self.datasources[layer].srid_out)
            else:
                srs.text = 'EPSG:4326'
            type.append(srs)

            # featureOperations = etree.Element('Operations')
            # featureOperations.append(etree.Element('Insert'))
            # featureOperations.append(etree.Element('Update'))
            # featureOperations.append(etree.Element('Delete'))
            # type.append(featureOperations)


            latlong = self.getLLBBOX(self.datasources[layer])
            type.append(latlong)

            featureList.append(type)

        return featureList

    def describefeaturetype(self):
        tree = etree.parse("resources/wfs-featuretype.xsd")
        root = tree.getroot()

        if len(self.layers) == 1:
            ''' special case when only one datasource is requested --> other xml schema '''
            root = self.addDataSourceFeatureType(root, self.datasources[self.layers[0]])
        else:
            ''' loop over all requested datasources '''
            for layer in self.layers:
                root = self.addDataSourceImport(root, self.datasources[layer])
                #root = self.addDataSourceFeatureType(root, self.datasources[layer])

        return etree.tostring(tree, pretty_print=True)

    def addDataSourceImport(self, root, datasource):
        root.append(
                    etree.Element('import', attrib={'namespace':self.namespaces['fs'],
                                                    'schemaLocation':self.host+'?request=DescribeFeatureType&typeName='+datasource.name})
                    )
        return root

    def addDataSourceFeatureType(self, root, datasource):

        root.append(etree.Element('element', attrib={'name':datasource.name,
                                                   'type':'fs:'+datasource.name+'_Type',
                                                   'substitutionGroup':'gml:_Feature'}))

        complexType = etree.Element('complexType', attrib={'name':datasource.name+'_Type'})
        complexContent = etree.Element('complexContent')
        extension = etree.Element('extension', attrib={'base':'gml:AbstractFeatureType'})
        sequence = etree.Element('sequence')

        for attribut_col in datasource.attribute_cols.split(','):
            type, length = datasource.getAttributeDescription(attribut_col)

            maxLength = etree.Element('maxLength', attrib={'value':str(length)})
            restriction = etree.Element('restriction', attrib={'base' : type})
            restriction.append(maxLength)
            simpleType = etree.Element('simpleType')
            simpleType.append(restriction)

            attrib_name = attribut_col
            if hasattr(datasource, "hstore"):
                if datasource.hstore:
                    attrib_name = self.getFormatedAttributName(attrib_name)

            element = etree.Element('element', attrib={'name' : str(attrib_name),
                                                       'minOccurs' : '0'})
            element.append(simpleType)

            sequence.append(element)

        if hasattr(datasource, "additional_cols"):
            for additional_col in datasource.additional_cols.split(';'):
                name = additional_col
                matches = re.search('(?<=[ ]as[ ])\s*\w+', str(additional_col))
                if matches:
                    name = matches.group(0)

                type, length = datasource.getAttributeDescription(name)

                maxLength = etree.Element('maxLength', attrib={'value':'0'})
                restriction = etree.Element('restriction', attrib={'base' : type})
                restriction.append(maxLength)
                simpleType = etree.Element('simpleType')
                simpleType.append(restriction)
                element = etree.Element('element', attrib={'name' : name,
                                                           'minOccurs' : '0',
                                                           'maxOccurs' : '0'})
                element.append(simpleType)

                sequence.append(element)


        if hasattr(datasource, 'geometry_type'):
            properties = datasource.geometry_type.split(',')
        else:
            properties = ['Point', 'Line', 'Polygon']
        for property in properties:
            if property == 'Point':
                element = etree.Element('element', attrib={'name' : datasource.geom_col,
                                                           'type' : 'gml:PointPropertyType',
                                                           'minOccurs' : '0'})
                sequence.append(element)
            elif property == 'Line':
                element = etree.Element('element', attrib={'name' : datasource.geom_col,
                                                           'type' : 'gml:LineStringPropertyType',
                                                           #'ref' : 'gml:curveProperty',
                                                           'minOccurs' : '0'})
                sequence.append(element)
            elif property == 'Polygon':
                element = etree.Element('element', attrib={'name' : datasource.geom_col,
                                                           'type' : 'gml:PolygonPropertyType',
                                                           #'substitutionGroup' : 'gml:_Surface',
                                                           'minOccurs' : '0'})
                sequence.append(element)


        extension.append(sequence)
        complexContent.append(extension)
        complexType.append(complexContent)
        root.append(complexType)

        return root

    def getBBOX(self, datasource):
        if hasattr(datasource, 'bbox'):
            coordstr = datasource.bbox
        else:
            coordstr = datasource.getBBOX()
        coordstr = coordstr.split(' ')

        return etree.Element('bbox',
                             attrib={'minx':coordstr[0],
                                     'miny':coordstr[1],
                                     'maxx':coordstr[2],
                                     'maxy':coordstr[3]})

    def getLLBBOX(self, datasource):
        if hasattr(datasource, 'LatLongBoundingBox '):
            latlong = datasource.LatLongBoundingBox
        else:
            latlong = datasource.getLLBBOX()
        latlongArray = latlong.split(' ')

        return etree.Element('{http://www.opengis.net/wfs}LatLongBoundingBox',
                             attrib={'minx':latlongArray[0],
                                     'miny':latlongArray[1],
                                     'maxx':latlongArray[2],
                                     'maxy':latlongArray[3]})
