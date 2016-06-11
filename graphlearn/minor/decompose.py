'''
decomposer for graphs and their minors.
extends the cips a normal decomposer is working with by cips that
take care of the minor graphs.
'''
from eden.modifier.graph import vertex_attributes
from eden.modifier.graph.structure import contraction
import graphlearn.decompose as graphtools
from graphlearn.decompose import Decomposer
import random
import logging
import networkx as nx
from graphlearn.utils import draw
import eden.util.display as edraw
import eden
logger = logging.getLogger(__name__)
from eden.graph import Vectorizer



def make_decomposergen(include_base=False, base_thickness_list=[2]):
    return lambda v, d: MinorDecomposer(v, d,
                                include_base=include_base,
                                base_thickness_list=base_thickness_list)

class MinorDecomposer(Decomposer):
    '''
    a wrapper normally wraps a graph.
    here we wrap a graph and also take care of its minor.
    '''

    def pre_vectorizer_graph(self, nested=False):
        '''
        generate the graph that will be used for evaluation ( it will be vectorized by eden and then used
        in a machine learning scheme).

        Parameters
        ----------
        nested: bool
            the graph returned here is the union of graph minor and the base graph.
            nested decides wether there edges between nodes in the base graph and their
            representative in the graph minor. these edges have the attribute 'nested'.

        Returns
        -------
            nx.graph
        '''
        g = nx.disjoint_union(self._base_graph, self.abstract_graph())
        node_id = len(g)

        if nested:
            for n, d in g.nodes(data=True):
                if 'contracted' in d and 'edge' not in d:
                    for e in d['contracted']:
                        if 'edge' not in g.node[e]:
                            # we want an edge from n to e
                            g.add_node(node_id, edge=True, label='e')
                            g.add_edge(n, node_id, nesting=True)
                            g.add_edge(node_id, e, nesting=True)
                            # g.add_edge( n, e, nesting=True)
                            node_id += 1

        return g

    def abstract_graph(self):
        '''

        Returns
        -------
        nx.graph
            returns the graph minor

        here i calculate the minor on demand.
        it is usualy more convenient to calculate the minor in the proprocessor.
        '''
        if self._abstract_graph == None:
            self._abstract_graph = make_abstract(self._base_graph, self.vectorizer)
        return self._abstract_graph


    def __init__(self,vectorizer=0, data=None,
                       include_base=False,
                       base_thickness_list=[2],node_entity_check=lambda x,y:True, nbit=20):
        '''

        Parameters
        ----------
        graph: nx.graph


        include_base: bool
            normally cores are at least as big as a node in the minor graph.
            enabling this will allow for extraction of cips from the base graph (that still have minor annotation).
            enables this: random_core_interface_pair_base, and if asked for all cips, basecips will be there too

        base_thickness_list:  list
            thickness for the base graph, i.e. how thick is the interface graph

        abstract_graph: graph
            provide the abstract graph

        Returns
        -------
        '''
        #print "asd",data
        self.some_thickness_list = base_thickness_list
        self.vectorizer = vectorizer
        if data:
            self._base_graph = data[0]
            if len(self._base_graph) > 0:
                self._base_graph = Vectorizer._edge_to_vertex_transform(self._base_graph)
            self._abstract_graph = data[1]
            self._mod_dict = self._abstract_graph.graph.get("mod_dict",{})  # this is the default.

        self.include_base = include_base  # enables this: random_core_interface_pair_base, and if asked for all cips, basecips will be there too

        self.node_entity_check = node_entity_check
        self.hash_bitmask = 2 ** nbit - 1
        self.nbit = nbit

    def make_new_decomposer(self, vectorizer, transformout):
        return MinorDecomposer(vectorizer, transformout, include_base=self.include_base,
                       base_thickness_list=self.some_thickness_list,
                       node_entity_check=self.node_entity_check, nbit=self.nbit)#node_entity_check=self.node_entity_check, nbit=self.nbit)



    def rooted_core_interface_pairs(self, root, thickness_list=None, for_base=False,radius_list=[], base_thickness_list=False):
        '''
             get cips for a root
        Parameters
        ----------
        root: int
            vertex id

        thickness: list

        for_base:bool
            do we want to extract from the base graph?

        **args: dict
            everything needed by extract_cips

        Returns
        -------


        '''
        if base_thickness_list:
            thickness = base_thickness_list
        else:
            thickness = self.some_thickness_list
        if for_base == False:
            return extract_cips(root, self, base_thickness_list=thickness, mod_dict=self._mod_dict,
                                        hash_bitmask=self.hash_bitmask,
                                      radius_list=radius_list,
                                      thickness_list=thickness_list,
                                      node_filter=self.node_entity_check)
        else:
            return extract_cips_base(root, self, base_thickness_list=thickness, mod_dict=self._mod_dict,
                                      hash_bitmask=self.hash_bitmask,
                                      radius_list=radius_list,
                                      thickness_list=thickness_list,
                                      node_filter=self.node_entity_check)

    def all_core_interface_pairs(self,
                                for_base=False,
                                radius_list=[],
                                thickness_list=None,
                                ):
        '''

        Parameters
        ----------
        args

        Returns
        -------

        '''
        graph=self.abstract_graph()
        nodes = filter(lambda x: self.node_entity_check(graph, x), graph.nodes())
        nodes = filter(lambda x: graph.node[x].get('APPROVEDABSTRACTNODE',True),nodes)

        cips = []
        for root_node in nodes:
            if 'edge' in graph.node[root_node]:
                continue
            cip_list = self.rooted_core_interface_pairs(root_node,
                                                        for_base=for_base,
                                                        radius_list=radius_list,
                                                        thickness_list=thickness_list)
            if cip_list:
                cips.append(cip_list)

        if self.include_base:
            graph = self.base_graph()
            for root_node in graph.nodes_iter():
                if 'edge' in graph.node[root_node]:
                    continue
                cip_list = self.rooted_core_interface_pairs(root_node,
                                                            for_base=self.include_base,

                                                            radius_list=radius_list,
                                                            thickness_list=thickness_list)
                if cip_list:
                    cips.append(cip_list)

        return cips

    def random_core_interface_pair(self,
                                   radius_list=None,
                                   thickness_list=None):
        '''
        get a random cip  rooted in the minor
        Parameters
        ----------
        radius_list: list
        thickness_list: list
        **args: dict
            args for rooted_core_interface_pairs

        Returns
        -------
            cip
        '''
        nodes = filter(lambda x: self.node_entity_check(self.abstract_graph(), x), self.abstract_graph().nodes())
        nodes =  filter(lambda x: self.abstract_graph().node[x].get('APPROVEDABSTRACTNODE',True),nodes)
        node = random.choice(nodes)
        if 'edge' in self._abstract_graph.node[node]:
            node = random.choice(self._abstract_graph.neighbors(node))
            # random radius and thickness
        radius_list = [random.choice(radius_list)]
        thickness_list = [random.choice(thickness_list)]
        random_something = [random.choice(self.some_thickness_list)]
        return self.rooted_core_interface_pairs(node, base_thickness_list=random_something,
                                        for_base=False,
                                      radius_list=radius_list,
                                      thickness_list=thickness_list)

    def random_core_interface_pair_base(self, radius_list=None, thickness_list=None, hash_bitmask=None,node_filter=lambda x, y: True):
        '''
        get a random cip, rooted in the base graph
        Parameters
        ----------
        radius_list
        thickness_list
        args

        Returns
        -------

        '''
        if self.include_base == False:
            raise Exception("impossible oOoo")
        node = random.choice(self.base_graph().nodes())
        if 'edge' in self._base_graph.node[node]:
            node = random.choice(self._base_graph.neighbors(node))
            # random radius and thickness
        radius_list = [random.choice(radius_list)]
        thickness_list = [random.choice(thickness_list)]
        random_something = [random.choice(self.some_thickness_list)]
        return self.rooted_core_interface_pairs(node, base_thickness_list=random_something, for_base=True,
                                          radius_list=radius_list,
                                          thickness_list=thickness_list,
                                     )


def check_and_draw(base_graph, abstr):
    '''

    Parameters
    ----------
    base_graph: a base graph
    abstr:  an abstract graph

    Returns
    -------
        check if EVERY node in base_graph is in any abstr.graph.node['contracted']
    '''
    nodeset = set([a for n, d in abstr.nodes(data=True) for a in d['contracted']])
    broken = []
    for n in base_graph.nodes():
        if n not in nodeset:
            broken.append(n)
            base_graph.node[n]['colo'] = .5
    if len(broken) > 0:
        print "FOUND SOMETHING BROKEN:"
        draw.set_ids(base_graph)
        base_graph.graph['info'] = 'failed to see these:%s' % str(broken)
        edraw.draw_graph(base_graph, vertex_label='id', vertex_color='colo', edge_label=None, size=20)
        for e, d in abstr.nodes(data=True):
            d['label'] = str(d.get('contracted', ''))
        edraw.draw_graph(abstr, vertex_label='label', vertex_color=None, edge_label=None, size=20)
        return False
    return True


def make_abstract(graph, vectorizer):
    '''
    graph should be the same expanded graph that we will feed to extract_cips later...
    Parameters
    ----------
    graph
    vectorizer

    Returns
    -------

    '''
    if isinstance(graph, nx.DiGraph):
        graph = graph.to_undirected()

    graph2 = vectorizer._revert_edge_to_vertex_transform(graph)
    graph2 = edge_type_in_radius_abstraction(graph2)
    graph2 = vectorizer._edge_to_vertex_transform(graph2)

    # find out to which abstract node the edges belong
    # finding out where the edge-nodes belong, because the contractor cant possibly do this
    getabstr = {contra: node for node, d in graph2.nodes(data=True) for contra in d.get('contracted', [])}

    for n, d in graph.nodes(data=True):
        if 'edge' in d:
            # if we have found an edge node...
            # lets see whos left and right of it:
            n1, n2 = graph.neighbors(n)
            # case1: ok those belong to the same gang so we most likely also belong there.
            if getabstr[n1] == getabstr[n2]:
                graph2.node[getabstr[n1]]['contracted'].add(n)

            # case2: neighbors belong to different gangs...
            else:
                blub = set(graph2.neighbors(getabstr[n1])) & set(graph2.neighbors(getabstr[n2]))
                for blob in blub:
                    if 'contracted' in graph2.node[blob]:
                        graph2.node[blob]['contracted'].add(n)
                    else:
                        graph2.node[blob]['contracted'] = set([n])
    return graph2


def edge_type_in_radius_abstraction(graph):
    '''
    # the function needs to set a 'contracted' attribute to each node with a set of vertices that
    # are contracted.
    Parameters
    ----------
    graph: any graph   .. what kind? expanded? which flags musst be set?

    Returns
    -------
    an abstract graph with node annotations that refer to the node ids it is contracting
    '''
    # annotate in node attribute 'type' the incident edges' labels
    labeled_graph = vertex_attributes.incident_edge_label(
            [graph], level=2, output_attribute='type', separator='.').next()
    # do contraction
    contracted_graph = contraction(
            [labeled_graph], contraction_attribute='type', modifiers=[], nesting=False).next()
    return contracted_graph


def extract_cips(node,
                 graphmanager,
                 base_thickness_list=None,
                 hash_bitmask=None,
                 mod_dict={},
                  radius_list=[],
                  thickness_list=None,
                  node_filter=lambda x, y: True
               ):
    '''

    Parameters
    ----------
    node: node in the abstract graph
    graphmanager
    base_thickness_list
    hash_bitmask
    mod_dict
    argz

    Returns
    -------
        a  list of cips
    '''

    # if not filter(abstract_graph, node):
    #    return []

    # PREPARE
    abstract_graph = graphmanager.abstract_graph()
    base_graph = graphmanager.base_graph()
    vectorizer = graphmanager.vectorizer
    if 'hlabel' not in abstract_graph.node[abstract_graph.nodes()[0]]:
        vectorizer._label_preprocessing(abstract_graph)
    if 'hlabel' not in base_graph.node[base_graph.nodes()[0]]:
        vectorizer._label_preprocessing(base_graph)

    # EXTRACT CIPS NORMALY ON ABSTRACT GRAPH
    abstract_cips = graphtools.extract_core_and_interface(node,
                                                          abstract_graph,
                                                          vectorizer=vectorizer,
                                                          hash_bitmask=hash_bitmask,
                                                          node_filter=node_filter,
                                                          radius_list=radius_list,
                                                          thickness_list=thickness_list)

    # VOR EVERY ABSTRACT CIP: MERGE CORE IN BASE GRAPH AND APPLY CIP EXTRACTON
    cips = []
    for abstract_cip in abstract_cips:
        base_copy, mergeids = merge_core(base_graph.copy(), abstract_graph, abstract_cip)
        base_level_cips = graphtools.extract_core_and_interface(mergeids[0],
                                                                base_copy,
                                                                vectorizer=vectorizer,
                                                                hash_bitmask=hash_bitmask,
                                                                node_filter=node_filter,
                                                                radius_list=[0],
                                                                thickness_list=base_thickness_list)

        # VOR EVERY BASE CIP: RESTORE CORE  AND  MERGE INFORMATION WITH ABSTRACT CIP
        core_hash = graphtools.graph_hash(base_graph.subgraph(mergeids), hash_bitmask=hash_bitmask)
        abstract_cip.core_nodes_count = len(mergeids)
        for base_cip in base_level_cips:
            cips.append(
                enhance_base_cip(base_cip, abstract_cip, mergeids, base_graph, hash_bitmask, mod_dict, core_hash))

    return cips


def enhance_base_cip(base_cip, abstract_cip, mergeids, base_graph, hash_bitmask, mod_dict, core_hash):
    '''

    Parameters
    ----------
    base_cip: cip
        a cip that was extracted from the base graph
    abstract_cip: cip
        a cip that was extracted from the abstract graph
    mergeids: list of int
        nodes in the base cip that are in the core of the abstract cip
    base_graph: graph
        the base graph
    hash_bitmask: int
        n/c
    mod_dict: dict
        {id in base_graph: modification to interface hash}
        if there is an exceptionaly important nodetype in thebase graph it makes sure
        that every substitution will preserve this nodetype Oo
        used eg to mark the beginning/end of rna sequences.
        endnode can only be replaced by endnode :)
    core_hash:
        hash for the core that will be used in the finished CIP

    Returns
    -------
        a finished? CIP
    '''
    # we cheated a little with the core, so we need to undo our cheating
    whatever = base_cip.graph.copy()
    base_cip.graph = base_graph.subgraph(base_cip.graph.nodes() + mergeids).copy()

    for n in mergeids:
        base_cip.graph.node[n]['core'] = True

    for n, d in base_cip.graph.nodes(data=True):
        if 'core' not in d:
            d['interface'] = True
            d['distance_dependent_label'] = whatever.node[n]['distance_dependent_label']

    base_cip.core_hash = core_hash
    # merging cip info with the abstract graph
    base_cip.interface_hash = eden.fast_hash_4(base_cip.interface_hash,
                                               abstract_cip.interface_hash,
                                               get_mods(mod_dict, mergeids), 0,
                                               hash_bitmask)

    base_cip.core_nodes_count = abstract_cip.core_nodes_count
    base_cip.radius = abstract_cip.radius
    base_cip.abstract_thickness = abstract_cip.thickness

    # i want to see what they look like :)
    base_cip.abstract_view = abstract_cip.graph
    base_cip.distance_dict = abstract_cip.distance_dict
    return base_cip


def merge_core(base_graph, abstract_graph, abstract_cip):
    """
    Parameters
    ----------
    base_graph: base graph. will be consumed
    abstract_graph:  we want the contracted info.. maybe we also find this in the cip.. not sure
    abstract_cip: the abstract cip

    Returns
    -------
        we merge all the nodes in the base_graph, that belong to the core of the abstract_cip

    """


    mergeids = [base_graph_id for radius in range(
            abstract_cip.radius + 1) for abstract_node_id in abstract_cip.distance_dict.get(radius)
                for base_graph_id in abstract_graph.node[abstract_node_id]['contracted']]

    # remove duplicates:
    mergeids = list(set(mergeids))

    for node_id in mergeids[1:]:
        graphtools.merge(base_graph, mergeids[0], node_id)

    return base_graph, mergeids


'''
a mod_dict is a modification dictionary.
use get_mod_dict to make a dict of nodenumber:associated_hash
if the nodenumber is in the core, the hash gets added to the interfacehash.
'''


def get_mods(mod_dict, nodes):
    su = 0
    for n in nodes:
        if n in mod_dict:
            su += mod_dict[n]
    return su


# here we create the mod dict once we have a graph..

def get_mod_dict(graph):
    return {}


def extract_cips_base(node,
                      graphmanager,
                      base_thickness_list=None,
                      hash_bitmask=None,
                      mod_dict={},
                      radius_list=[],
                      thickness_list=None,
                      node_filter=lambda x, y: True):
    '''
    Parameters
    ----------
    node: int
        id of a node
    graphmanager: graph-wrapper
        the wrapper that contains the graph
    base_thickness_list: [int]
        thickness of SOMETHING
    hash_bitmask: int
        see above
    mod_dict: dict
        see above
    **argz: dict
        more args
        I guess these are meant:
        radius_list=None,
        thickness_list=None,
        vectorizer=Vectorizer(),
        node_filter=lambda x, y: True):

    Returns
    -------
        [CIP]
        a list of core_interface_pairs
    '''

    # if not filter(abstract_graph, node):
    #    return []

    # PREPARE
    abstract_graph = graphmanager.abstract_graph()
    base_graph = graphmanager.base_graph()
    vectorizer = graphmanager.vectorizer
    if 'hlabel' not in abstract_graph.node[abstract_graph.nodes()[0]]:
        vectorizer._label_preprocessing(abstract_graph)
    if 'hlabel' not in base_graph.node[base_graph.nodes()[0]]:
        vectorizer._label_preprocessing(base_graph)

    # LOOK UP ABSTRACT GRAPHS NODE AND
    # EXTRACT CIPS NORMALY ON ABSTRACT GRAPH
    for n, d in abstract_graph.nodes(data=True):
        if node in d['contracted']:
            abs_node = n
            break
    else:
        raise Exception("IMPOSSIBLE NODE")


    abstract_cips = graphtools.extract_core_and_interface(root_node=abs_node,
                                                          graph=abstract_graph,
                                                          vectorizer=vectorizer,
                                                          hash_bitmask=hash_bitmask,
                                                          radius_list=[0],
                                                          thickness_list=thickness_list,
                                                          node_filter=node_filter )

    # VOR EVERY ABSTRACT CIP: EXTRACT BASE CIP
    cips = []

    for abstract_cip in abstract_cips:

        base_level_cips = graphtools.extract_core_and_interface(node,
                                                                base_graph,
                                                                vectorizer=vectorizer,
                                                                hash_bitmask=hash_bitmask,
                                                                radius_list=radius_list,
                                                                thickness_list=base_thickness_list )
        # VOR EVERY BASE CIP: hash interfaces and save the abstract view
        for base_cip in base_level_cips:
            cores = [n for n, d in base_cip.graph.nodes(data=True) if 'interface' not in d]
            base_cip.interface_hash = eden.fast_hash_4(base_cip.interface_hash,
                                                       abstract_cip.interface_hash,
                                                       get_mods(mod_dict, cores), 1337,
                                                       hash_bitmask)
            base_cip.abstract_view = abstract_cip.graph
            cips.append(base_cip)

    return cips
root_node=None,
