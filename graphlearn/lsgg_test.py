

import networkx as nx
import lsgg
import eden.graph as eg
from graphlearn.utils import ascii

import lsgg_compose_util as lcu
from eden.graph import _label_preprocessing
from eden.graph import _edge_to_vertex_transform


def edenize(g):
    for n in g.nodes():
        g.node[n]['label']=str(n)

    for a,b in g.edges():
        g[a][b]['label']='.'
    return _edge_to_vertex_transform(g)

def prep_cip_extract(g):
    g= edenize(g)
    _label_preprocessing(g)
    return g

def get_grammar():
    lsggg=lsgg.lsgg()
    g=prep_cip_extract(nx.path_graph(4))
    lsggg.fit([g,g,g])
    return lsggg



def test_fit():
    lsggg= get_grammar()

    assert( 4 == sum( len(e)  for e in lsggg.productions.values()) )
    assert(43568 in lsggg.productions[29902])
    assert(32346 in lsggg.productions[29902])
    assert(3760 in lsggg.productions[49532])
    assert(30237 in lsggg.productions[49532])
test_fit()


def test_extract_core_and_interface():
    graph=nx.path_graph(4)
    prep_cip_extract(graph)
    res = lcu.extract_core_and_interface(root_node=3, graph=graph, radius=1,thickness=1)
    assert ( str(res) == "cip: int:213722, cor:681116, rad:1, thi:1, rot:3")
test_extract_core_and_interface()


def test_neighbors():
    # make a grammar
    lsggg = get_grammar()

    #make agraph
    g=nx.path_graph(4)
    g=edenize(g)
    g.node[3]['label']='5'
    assert(6 ==  len(list(lsggg.neighbors(g))))
test_neighbors()
