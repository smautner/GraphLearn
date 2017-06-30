import random
import graphlearn2.graphlearn.lsgg as base_grammar

class lsgg(base_grammar.lsgg):
    def some_neighbors(self,graph,num_neighbors):
        self.label_preprocessing(graph)
        nodes=[n for n in graph.nodes() if 'edge' not in graph.node[n]]
        random.shuffle(nodes)
        for n in nodes:
            for orig_cip in self._rooted_decompose(graph,n):
                for graph2 in self._neighbors_given_orig_cips(graph, [orig_cip]):
                    if num_neighbors > 0:
                        num_neighbors -= 1
                        yield graph2
                    else:
                        raise StopIteration





