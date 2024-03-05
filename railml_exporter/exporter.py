from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree, Element, SubElement

from yaramo.edge import Edge
from yaramo.node import Node
from yaramo.topology import Topology


class Exporter:
    def __init__(self, topology):
        self.topology: Topology = topology
        self.root = Element("railML", **{"version": "3.1",
                                    "xmlns": "https://www.railml.org/schemas/3.2",
                                    "xmlns:dc": "http://purl.org/dc/elements/1.1/",
                                    "xmlns:gml": "http://www.opengis.net/gml/3.2/",
                                    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
                                    "xsi:schemaLocation": "https://www.railml.org/schemas/3.2 https://www.railml.org/schemas/3.2/railml3.xsd",
                                    })
        self.infra = SubElement(self.root, "infrastructure", id=self.topology.name or self.topology.uuid)
        self.topo = SubElement(self.infra, "topology")
        self.netElements = SubElement(self.topo, "netElements")
        self.netRelations = SubElement(self.topo, "netRelations")
        self.networks = SubElement(self.topo, "networks")
        self.network = SubElement(self.networks, "network", id="nw01")
        self.level = SubElement(self.network, "level", id="lv01", descriptionLevel="Micro")
        self.tree = self.generate_xml()

    def _add_relation(self, edge: Edge, at_node: Node):
        '''
        Generate the relation between the edge and the node
        :param edge: The edge to generate the relation for
        :param at_node: At which yaramo node (e.g. switch) the relation is realised
        :return: ElementTree.Element of the relation
        '''
        edge_forward = edge.node_a.uuid == at_node.uuid
        relation = SubElement(self.netRelations, "netRelation", id=f"{edge.node_a}-{edge.node_b}",
                                   positionOnA="0" if edge_forward else "1", positionOnB="1" if edge_forward else "0", navigability="Both")
        SubElement(relation, "elementA", ref=edge.node_a.uuid)
        SubElement(relation, "elementB", ref=edge.node_a.uuid)
        SubElement(self.level, "networkResource", ref=relation.get("id"))

    def generate_xml(self) -> ElementTree:

        for edge in self.topology.edges.values():
            # every yaramo edge is a railML netElement
            SubElement(self.netElements, "netElement", id=edge.uuid)
            SubElement(self.level, "networkResource", ref=edge.uuid)
        for node in self.topology.nodes.values():
            if not all([node.connected_on_left, node.connected_on_right, node.connected_on_head]):
                node.calc_anschluss_of_all_nodes()

            # every yaramo node realises a relation between the connected edges/railML net elements
            edge_head = self.topology.get_edge_by_nodes(node, node.connected_on_head)
            edge_left = self.topology.get_edge_by_nodes(node, node.connected_on_left)
            edge_right = self.topology.get_edge_by_nodes(node, node.connected_on_right)
            self._add_relation(edge_head, node)
            self._add_relation(edge_left, node)
            self._add_relation(edge_right, node)

            # adding the relation between the two branches of the switch that are non-navigable and don't have an edge in yaramo
            relation = SubElement(self.netRelations, "netRelation", id=f"{node.connected_on_left}-{node.connected_on_right}", positionOnA="1" if edge_left.node_a.uuid == node.uuid else "0", positionOnB="1" if edge_right.node_a.uuid == node.uuid else "0", navigability="None")
            SubElement(relation, "elementA", ref=node.connected_on_left.uuid)
            SubElement(relation, "elementB", ref=node.connected_on_right.uuid)
            SubElement(self.level, "networkResource", ref=relation.get("id"))

        return ElementTree(self.root)

    def to_string(self):
        return ET.tostring(self.tree.getroot(), encoding='utf-8', method='xml')

    def to_file(self, filename):
        self.tree.write(filename)
