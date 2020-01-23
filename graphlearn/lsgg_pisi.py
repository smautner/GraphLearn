from graphlearn import lsgg 
import structout as so
from graphlearn import lsgg_cip
import networkx as nx
import numpy as np
import random
import  scipy.sparse as sparse
import logging
logger = logging.getLogger(__name__)
from sklearn.metrics.pairwise import cosine_similarity


class PiSi(lsgg.lsgg_sample):

    def _extract_cip(self, **kwargs):
        return extract_cip(thickness_pisi=2*self.decomposition_args['thickness_pisi'],
                                          **kwargs)
    
    def _congruent_cips(self, cip):
        cips = self.productions.get(cip.interface_hash, {}).values()
        if len(cips) == 0:
            logger.log(10,"no congruent cip in grammar")
        else: 
            cips_ = [(cip_,np.max( cip_.pisi_vectors.dot(cip.pisi_vectors.toarray()[0])))
                         for cip_ in cips if cip_.core_hash != cip.core_hash]
             
            cips_ = [ (a,b) for a,b in cips_ if b > 0]

            if len(cips_) == 0: logger.log(10,"0 cips with pisi-similarity > 0")
            for cip_, di in cips_:
                cip_.pisisimilarity=di
                yield cip_
    
    def _neighbors_sample_order_proposals(self,subs): 
        sim = [c[1].pisisimilarity for c in subs ]
        logger.log(10, "pisi similarities: "+str(sim))
        p_size = [a*b for a,b in zip (self.get_size_proba(subs),sim)]
        return self.order_proba(subs, p_size)


    def _add_cip(self, cip):
                    
        grammarcip = self.productions[cip.interface_hash].setdefault(cip.core_hash, cip)
        grammarcip.count+=1
        if not grammarcip.pisi_hash.intersection(cip.pisi_hash): 
            grammarcip.pisi_vectors= sparse.vstack( (grammarcip.pisi_vectors,  cip.pisi_vectors))
            grammarcip.pisi_hash= grammarcip.pisi_hash.union(cip.pisi_hash)

    def __repr__(self):
        """repr."""
        n_interfaces, n_cores, n_cips, n_productions = self.size()
        txt = '#interfaces: %5d   ' % n_interfaces
        txt += '#cores: %5d   ' % n_cores
        txt += '#core-interface-pairs: %5d   ' % n_cips
        txt += '#production-rules: %5d   ' % n_productions
        txt += '#pisi vectors: %5d   ' % len(set().union(*[ cip.pisi_hash for v in self.productions.values() for cip in v.values()   ]))
        txt += '#count sum: %5d   ' % sum([ cip.count for v in self.productions.values() for cip in v.values()   ])
        return txt


def extract_cip(root_node=None,
                               graph=None,
                               radius=None,
                               thickness=None,
			       thickness_pisi=2):
   
    # MAKE A NORMAL CIP AS IN LSGG_CIP
    graph =  lsgg_cip._edge_to_vertex(graph)
    lsgg_cip._add_hlabel(graph)
    dist = {a:b for (a,b) in lsgg_cip.short_paths(graph,
                                         root_node if isinstance(root_node,list) else [root_node],
                                         radius+max(thickness_pisi,thickness))}

    core_nodes = [id for id, dst in dist.items() if dst <= radius]
    interface_nodes = [id for id, dst in dist.items()
                       if radius < dst <= radius + thickness]

    normal_cip =  lsgg_cip._finalize_cip(root_node,graph,radius,thickness,dist,core_nodes,interface_nodes)


    # NOW COMES THE pisi PART

    pisi_nodes = [id for id, dst in dist.items()
                       if radius+1 < dst <= (radius + thickness_pisi)]

    pisi_graph = graph.subgraph(pisi_nodes) 
    
    loosecontext = nx.Graph(pisi_graph)
    if loosecontext.number_of_nodes() > 2:
        normal_cip.pisi_vectors = lsgg_cip.eg.vectorize([loosecontext])
        lsgg_cip._add_hlabel(loosecontext)
        normal_cip.pisi_hash = set([ lsgg_cip.graph_hash(loosecontext)] ) 
        return normal_cip
    return None


