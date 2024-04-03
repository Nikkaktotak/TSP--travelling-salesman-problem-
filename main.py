import tsplib95
import matplotlib.pyplot as plt
import networkx as nx
import time

from colony import Colony
from solver import Solver

import xml.etree.ElementTree as ET


def read_xml_graph(file_path):
    tree = ET.parse(file_path)
    root = tree.getroot()

    G = nx.Graph()

    vertex_id = 0
    for vertex in root.findall('./graph/vertex'):
        G.add_node(vertex_id)
        vertex_id += 1

    vertex_id = 0
    for vertex in root.findall('./graph/vertex'):
        for edge in vertex.findall('./edge'):
            neighbor_id = int(edge.text)
            cost = float(edge.attrib['cost'])
            G.add_edge(vertex_id, neighbor_id, weight=cost)
        vertex_id += 1

    return G

#problem = tsplib95.load_problem('bays29.tsp')
#G = problem.get_graph()
G = read_xml_graph('eil101.xml')

solver = Solver()
colony = Colony(2, 4)
sales = 1

ans = solver.solve(G, colony, sales, start=100, limit=50, opt2=20)
#stopwatch
start_time = time.time()
for i in range(10):
    print(f'Iteration {i}')
    ans = solver.solve(G, colony, sales, start=41, limit=50, opt2=20)
    print(sum(s.cost for s in ans))
    print(ans)
    print("--- %s seconds ---" % (time.time() - start_time))
    start_time = time.time()
#summary time
print("--- %s seconds ---" % (time.time() - start_time))