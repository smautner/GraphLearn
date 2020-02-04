#!/usr/bin/env python

"""Provides the graph grammar class."""

from collections import defaultdict
from graphlearn import lsgg_core_interface_pair
import logging

logger = logging.getLogger(__name__)
from graphlearn.util.multi import mpmap


class LocalSubstitutionGraphGrammarCore(object):
    def __init__(self,
                 radii=[0,1],
                 thickness = 1,
                 filter_min_cip = 2,
                 filter_min_interface =2,
                 double_radius_and_thickness=True
                 ):
        """Parameters
        ----------
        decomposition_args:
        filter_args
        cip_root_all : include edges as possible roots
        double_decomp_args: interpret options for radius and thickness 
                as half step (default is full step)
        """
        self.radii = radii
        self.thickness= thickness
        self.filter_min_cip = filter_min_cip
        self.filter_min_interface = filter_min_interface

        self.productions = defaultdict(dict)
        if  double_radius_and_thickness:
            self.double_radius_and_thickness()

    def double_radius_and_thickness(self):
            self.radii = [i*2 for i in self.radii]
            self.thickness = 2 * self.thickness



    ###########
    # FITTING
    ##########
    def fit(self, graphs):
        self._store_graphs(graphs)
        self._filter_cips()
        return self
    

    def _store_graphs(self, graphs):
        for graph in graphs:
            self._store_graph(graph)

    def _store_graph(self, graph):
        for cip in self._make_cips(graph):
                self._store_cip(cip)


    def _make_cips(self, graph):
        for root in self._get_cores(graph):
                x = self._make_cip(core=root, graph=graph)
                if x:
                    yield x


    def _make_cip(self, core=None, graph=None):
        return lsgg_core_interface_pair.CoreInterfacePair(
                                   core=core,
                                   graph=graph,
                                   thickness=self.thickness)


    def _store_cip(self, cip):
        # setdefault is a fun function
        self.productions[cip.interface_hash].setdefault(cip.core_hash, cip).count += 1

    def _filter_cips(self):
        logger.log(10,"grammar bevore freq filter: %s" % str(self))
        """Remove infrequent cores and interfaces. see fit"""
        for interface in list(self.productions.keys()):
            for core in list(self.productions[interface].keys()):
                if self.productions[interface][core].count < self.filter_min_cip:
                    self.productions[interface].pop(core)
            if len(self.productions[interface]) < self.filter_min_interface:
                self.productions.pop(interface)
        logger.log(10, self)

    ##############
    #  APPLYING A PRODUCTION
    #############
    def _get_congruent_cips(self, cip):
        """all cips in the grammar that are congruent to cip in random order.
        congruent means they have the same interface-hash-value"""
        cips = self.productions.get(cip.interface_hash, {}).values()
        cips_ = [cip_ for cip_ in cips if cip_.core_hash != cip.core_hash]
        return cips_

    def _substitute_core(self, graph, cip, cip_):
        return lsgg_core_interface_pair.substitute_core(graph, cip, cip_)

    def neighbors(self, graph):
        """iterator over all neighbors of graph (that are conceiveable by the grammar)"""
        for cip in self._make_cips(graph):
            for congruent_cip in self._get_congruent_cips(cip):
                graph_ = self._substitute_core(graph, cip, congruent_cip)
                if graph_ is not None:
                    yield graph_

    def _get_cores(self, graph):
        return [ core for core in lsgg_core_interface_pair.get_cores(graph, self.radii) if core]

  
    def __repr__(self):
        return "interfaces %d cores: %d " % \
               ( len(self.productions), len(set([i.core_hash for v in self.productions.values() for i in v])))
    


class LocalSubstitutionGraphGrammar(LocalSubstitutionGraphGrammarCore):

    def neighbors_root(self, graph, root):
        """iterator over all neighbors of graph (that are conceiveable by the grammar)"""
        cip= self._make_cip(root, graph)
        for congruent_cip in self._get_congruent_cips(cip):
            graph_ = self._substitute_core(graph, cip, congruent_cip)
            if graph_ is not None:
                yield graph_

    def is_fit(self):
        return len(self.productions) > 0 

    ########
    # print
    ########
    def size(self):
        """size."""
        n_interfaces = len(self.productions)

        cores = set()
        n_productions = 0
        for interface in self.productions.keys():
            n_productions += len(self.productions[interface]) * (len(self.productions[interface]) - 1)
            for core in self.productions[interface].keys():
                cores.add(core)

        n_cores = len(cores)
        n_cips = sum(len(self.productions[interface])
                     for interface in self.productions)

        return n_interfaces, n_cores, n_cips, n_productions

    def __repr__(self):
        """repr."""
        n_interfaces, n_cores, n_cips, n_productions = self.size()
        txt = '#interfaces: %5d   ' % n_interfaces
        txt += '#cores: %5d   ' % n_cores
        txt += '#core-interface-pairs: %5d  ' % n_cips
        txt += '#production-rules: %5d' % n_productions
        return txt

    def fit(self, graphs, n_jobs=1):
        if n_jobs==1:
            return super( LocalSubstitutionGraphGrammar, self ).fit(graphs)

        # this provides parallelism
        for ciplist in mpmap(self._make_cips_list, graphs, poolsize=n_jobs):
            for cip in ciplist:
                self._store_cip(cip)

        self._filter_cips()
        return self

    def _make_cips_list(self, graph):
        return list(self._make_cips(graph))