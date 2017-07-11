import random
import utils
from collections import defaultdict
from eden.graph import _label_preprocessing




from lsgg_compose_util import extract_core_and_interface, core_substitution
import utils_display as ud
import logging
logger = logging.getLogger(__name__)



class lsgg(object):
    def __init__(self,
                 decompositionargs={"radius_list":[0,2],"thickness_list":[2,4],'hash_bitmask':2**16-1},
                 filterargs={"min_cip_count":2,"min_interface_count":2}
                 ):

        self.productions=defaultdict(dict)
        self.decompositionargs=decompositionargs
        self.filterargs=filterargs


    def label_preprocessing(self,graph):
        _label_preprocessing(graph)

    ###########
    #  FITTING
    ##########
    def fit(self,graphs):
        self._add(graphs)
        self._filter()

    def _add(self, graphs):
        for g in graphs:
            for cip in self._decompose(g):
                self._production_add_cip(cip)

    def _rooted_decompose(self,graph,root):
        for radius in self.decompositionargs['radius_list']:
            for thickness in self.decompositionargs['thickness_list']:
                yield extract_core_and_interface(root_node=root,
                                                     graph=graph,
                                                     radius=radius,
                                                     thickness=thickness,
                                                     hash_bitmask=self.decompositionargs['hash_bitmask'])

    def _decompose(self, graph):
        _label_preprocessing(graph)
        for root in [ n for n in graph.nodes() if 'edge' not in graph.node[n]]:
            for e in self._rooted_decompose(graph,root):
                yield e



    def _production_add_cip(self, cip):
        # setdefault is a fun function
        self.productions[cip.interface_hash].setdefault(cip.core_hash, cip).count+=1

    def _filter(self):
        '''
        removes cores that have not been seen often enough
        removes interfaces that have too few cores
        '''
        for interface in self.productions.keys():
            for core in self.productions[interface].keys():
                if self.productions[interface][core].count < self.filterargs['min_cip_count']:
                    self.productions[interface].pop(core)
            if len(self.productions[interface]) < self.filterargs['min_interface_count']:
                self.productions.pop(interface)

    ############
    # apply production
    ###########

    def _substitute(self, graph, orig_cip, new_cip):
        r = core_substitution(graph, orig_cip.graph, new_cip.graph)
        #ud.gprint( [graph, orig_cip.graph, new_cip.graph, r ])
        return r

    def _suggest_new_cips(self, graph, orig_cip):
            v = [e for e in self.productions[orig_cip.interface_hash].values()
                 if e.core_hash !=orig_cip.core_hash]
            random.shuffle(v)
            return v

    def _neighbors_given_orig_cips(self, graph, original_cips):
        for orig in original_cips:
            candidates_new = self._suggest_new_cips(graph, orig)
            for new in candidates_new:
                r = self._substitute(graph,orig,new)
                (yield r) if r else logger.log(5,'lsgg: a substitution returned None')

    def neighbors(self,graph):
        _label_preprocessing(graph)
        for e in self._neighbors_given_orig_cips(graph, self._decompose(graph)):
            yield e


