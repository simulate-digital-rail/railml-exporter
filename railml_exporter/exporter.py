from uuid import uuid4
from xml.etree import ElementTree as ET
from xml.etree.ElementTree import ElementTree, Element, SubElement

from yaramo.edge import Edge
from yaramo.node import Node
from yaramo.signal import SignalDirection, Signal, SignalKind, SignalFunction
from yaramo.topology import Topology


class Exporter:
    def __init__(self, topology):
        self.topology: Topology = topology
        self.root = Element("railML", **{"version": "3.2",
                                         "xmlns": "https://www.railml.org/schemas/3.2",
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
        self.funcInfra = SubElement(self.infra, "functionalInfrastructure")
        self.switchesIS = SubElement(self.funcInfra, "switchesIS")
        self.signalsIS = SubElement(self.funcInfra, "signalsIS")
        self.tracks = SubElement(self.funcInfra, "tracks")
        self.interlocking = SubElement(self.root, "interlocking")
        assetsIL = SubElement(self.interlocking, "assetsForInterlockings")
        self.assetsIL = SubElement(assetsIL, "assetsForInterlocking", id="af01")
        self.signalsIL = SubElement(self.assetsIL, "signalsIL")
        self.switchesIL = SubElement(self.assetsIL, "switchesIL")
        self.tree = self.generate_xml()

    def _add_relation(self, edge1: Edge, edge2: Edge, at_node: Node, navigability: str = "Both"):
        edge1_starts_here = edge1.node_a.uuid == at_node.uuid
        edge2_starts_here = edge2.node_a.uuid == at_node.uuid
        relation = SubElement(self.netRelations, "netRelation", id=f"{edge1}-{edge2}",
                              positionOnA="0" if edge1_starts_here else "1",
                              positionOnB="0" if edge2_starts_here else "1", navigability=navigability)
        SubElement(relation, "elementA", ref=edge1.uuid)
        SubElement(relation, "elementB", ref=edge2.uuid)
        SubElement(self.level, "networkResource", ref=relation.get("id"))
        return relation

    def _get_signal_function(self, signal: Signal):
        if signal.kind == SignalKind.Vorsignal:
            return "distant"
        elif signal.kind == SignalKind.Sperrsignal:
            return "barrage"
        elif signal.function == SignalFunction.Ausfahr_Signal:
            return "exit"
        elif signal.function == SignalFunction.Einfahr_Signal:
            return "entry"
        elif signal.function == SignalFunction.Block_Signal:
            return "block"
        return None

    def generate_xml(self) -> ElementTree:

        for edge in self.topology.edges.values():
            # every yaramo edge is a railML netElement
            ne = SubElement(self.netElements, "netElement", id=edge.uuid)
            ps = SubElement(ne, "associatedPositioningSystem", id=str(uuid4()))
            SubElement(ps, "intrinsicCoordinate", id=str(uuid4()), intrinsicCoord="0")
            SubElement(ps, "intrinsicCoordinate", id=str(uuid4()), intrinsicCoord="1")
            SubElement(self.level, "networkResource", ref=edge.uuid)
            SubElement(self.tracks, "track", id=f"trc_{edge.uuid}", type="mainTrack")
        for node in self.topology.nodes.values():
            if len(node.connected_nodes) == 3:
                if not all([node.connected_on_left, node.connected_on_right, node.connected_on_head]):
                    node.calc_anschluss_of_all_nodes()

                # every yaramo node realises a relation between the connected edges/railML net elements
                edge_head = self.topology.get_edge_by_nodes(node, node.connected_on_head)
                edge_left = self.topology.get_edge_by_nodes(node, node.connected_on_left)
                edge_right = self.topology.get_edge_by_nodes(node, node.connected_on_right)
                rel_left = self._add_relation(edge_head, edge_left, node)
                rel_right = self._add_relation(edge_head, edge_right, node)
                self._add_relation(edge_left, edge_right, node, navigability="None")

                switch = SubElement(self.switchesIS, "switchIS", id=node.uuid,  type="ordinarySwitch")
                if node.turnout_side is not None:
                    switch.set("continueCourse", "right" if node.turnout_side == "left" else "left")
                    switch.set("branchCourse", node.turnout_side)
                name = SubElement(switch, "name", name=node.name or node.uuid, language="en")
                left = SubElement(switch, "leftBranch", netRelationRef=rel_left.get("id"))
                if node.maximum_speed_on_left:
                    left.set("branchingSpeed", node.maximum_speed_on_left)
                    left.set("joiningSpeed", node.maximum_speed_on_left)
                right = SubElement(switch, "rightBranch", netRelationRef=rel_right.get("id"))
                if node.maximum_speed_on_right:
                    right.set("branchingSpeed", node.maximum_speed_on_right)
                    right.set("joiningSpeed", node.maximum_speed_on_right)
                SubElement(switch, "spotLocation", id=str(uuid4()), netElementRef=edge_head.uuid, pos="0" if edge_head.node_a.uuid == node.uuid else "1", applicationDirection="normal")
                SubElement(switch, "locationReference", referencePoint="switchCenter", tangentLength="5")
                switch_il = SubElement(self.switchesIL, "switchIL", id=f"pt_{node.uuid}")
                SubElement(switch_il, "refersTo", ref=node.uuid)
                SubElement(switch_il, "branchLeft", ref=f"trc_{edge_left.uuid}")
                SubElement(switch_il, "branchRight", ref=f"trc_{edge_right.uuid}")
        for yaramo_signal in self.topology.signals.values():
            signal = SubElement(self.signalsIS, "signalIS", id=yaramo_signal.uuid, isSwitchable="true")
            SubElement(signal, "isTrainMovementSignal")
            yaramo_signal.edge.update_length()
            SubElement(signal, "spotLocation", id=str(uuid4()), netElementRef=yaramo_signal.edge.uuid, pos=str(yaramo_signal.distance_edge / yaramo_signal.edge.length), applicationDirection="normal" if yaramo_signal.direction == SignalDirection.IN else "reverse")
            if yaramo_signal.name:
                SubElement(signal, "name", name=yaramo_signal.name, language="en")
            signal_il = SubElement(self.signalsIL, "signalIL", id=str(uuid4()))
            if function := self._get_signal_function(yaramo_signal):
                signal_il.set("function", function)

        return ElementTree(self.root)

    def to_string(self):
        return ET.tostring(self.tree.getroot(), encoding='utf-8', method='xml')

    def to_file(self, filename):
        self.tree.write(filename)
