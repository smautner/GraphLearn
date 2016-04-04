import logging

import eden.converter.rna as converter

from graphlearn.abstract_graphs.rna import expanded_rna_graph_to_digraph, get_sequence
from graphlearn.abstract_graphs.rna.fold import EdenNNF
from graphlearn.abstract_graphs.rna.rnadecomposer import RnaDecomposer
from graphlearn.transform import GraphTransformer

logger = logging.getLogger(__name__)
from graphlearn.transform import PostProcessor


class PostProcessor(PostProcessor):
    def re_transform_single(self, input):
        return self.pp.re_transform_single(input)


class GraphTransformerForgi(GraphTransformer):
    def __init__(self, base_thickness_list=[2], structure_mod=True, include_base=False, ignore_inserts=False):
        '''

        Parameters
        ----------
        base_thickness_list: list of int
            thickness list for the base graph
        structure_mod : bool
            should we introduce "F" nodes to keep multiloop flexible regarding substitution
        include_base : base
            if asked for all cips, i will also yield   "normal" cips (whose core is not radius of abstract, but radius of base graph)
        ignore_inserts:
            bolges will be ignored and merged to their adjacend stems

        Returns
        -------

        '''
        self.ignore_inserts = ignore_inserts
        self.base_thickness_list = [thickness * 2 for thickness in base_thickness_list]
        self.structure_mod = structure_mod
        self.include_base = include_base

    def fit(self, inputs, vectorizer):
        """

        Parameters
        ----------
        inputs: sequence list
        vectorizer: a vectorizer

        Returns
        -------
        self
        """

        self.vectorizer = vectorizer
        self.NNmodel = EdenNNF(n_neighbors=4,structure_mod=self.structure_mod)
        self.NNmodel.fit(inputs)
        return self

    def fit_transform(self, inputs):
        """

        Parameters
        ----------
        inputs: sequences

        Returns
        -------
        many graphdecomposers
        """

        inputs = list(inputs)
        self.fit(inputs, self.vectorizer)
        inputs = [b for a, b in inputs]
        return self.transform(inputs)

    def re_transform_single(self, graph):
        """

        Parameters
        ----------
        graph: digraph

        Returns
        -------
        graph decomposer
        """

        try:
            sequence = get_sequence(graph)
        except:
            logger.debug('sequenceproblem: this is not an rna')
            # draw.graphlearn(graph, size=20)
            return None

        sequence = sequence.replace("F", '')
        trans = self.transform([sequence])[0]
        # if trans._base_graph.graph['energy'] > -10:
        #    return None
        return trans

    def transform(self, sequences):
        """

        Parameters
        ----------
        sequences : iterable over rna sequences

        Returns
        -------
        list of RnaGraphWrappers
        """
        result = []
        for sequence in sequences:

            # if we eat a tupple, it musst be a (name, sequence) type :)  we only want a sequence
            if type(sequence) == type(()):
                logger.warning('YOUR INPUT IS A TUPPLE, GIVE ME A SEQUENCE, SINCERELY -- YOUR RNA PREPROCESSOR')

            # get structure
            structure, energy, sequence = self.NNmodel.transform_single(('fake', sequence))
            if structure == None:
                result.append(None)
                continue


            # built base_graph
            base_graph = converter.sequence_dotbracket_to_graph(seq_info=sequence, seq_struct=structure)
            base_graph = self.vectorizer._edge_to_vertex_transform(base_graph)
            base_graph = expanded_rna_graph_to_digraph(base_graph)
            base_graph.graph['energy'] = energy
            base_graph.graph['sequence'] = sequence
            base_graph.graph['structure'] = structure
            result.append(
                    RnaDecomposer(sequence, structure, base_graph, self.vectorizer, self.base_thickness_list,
                                  include_base=self.include_base, ignore_inserts=self.ignore_inserts)
            )
        return result


'''
default method if no nearest neighbor folding class is provided
# is never used .. so we disable it
def callRNAshapes(sequence):
    cmd = 'RNAshapes %s' % sequence
    out = sp.check_output(cmd, shell=True)
    s = out.strip().split('\n')

    for li in s[2:]:
        # print li.split()
        energy, shape, abstr = li.split()
        # if abstr == '[[][][]]':
        return shape
'''



