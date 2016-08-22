'''
automatic minor graph generation
'''
import transform
#import decompose
import graphlearn.utils.draw as draw
#from sklearn.cluster import MiniBatchKMeans
#import sklearn.cluster as cluster


class Cascade():
    def __init__(self,  depth=2,
                        debug=False,
                        multiprocess=True,
                 max_group_size=6,min_group_size=2):

        self.depth = depth
        self.debug = debug
        self.multiprocess = multiprocess
        self.max_group_size = max_group_size
        self.min_group_size =min_group_size

    def setup_transformers(self):
        self.transformers = []
        for i in range(self.depth):
            transformer = transform.GraphMinorTransformer(


                group_score_threshold= -.5,
                group_max_size=self.max_group_size,
                group_min_size=self.min_group_size,
                multiprocess=self.multiprocess,
                # cluster_max_members=-1,
                layer=i,
                debug=self.debug)
            self.transformers.append(transformer)

    def fit_transform(self, graphs, graphs_neg=[],remove_intermediary_layers=True):

        # INIT
        self.setup_transformers()
        for g in graphs+graphs_neg:
            g.graph['layer']=0

        # fitting
        for i in range(self.depth):
            graphs, graphs_neg = self.transformers[i].fit_transform(graphs,graphs_neg)

        if remove_intermediary_layers:
            graphs,graphs_neg= self.do_remove_intermediary_layers(graphs,graphs_neg)

        return graphs,graphs_neg

    def fit(self, graphs, g2=[]):
        self.fit_transform(graphs,g2)
        return self

    def transform(self, graphs,g2=[], remove_intermediary_layers=True):
        for g in graphs+g2:
            g.graph['layer']=0
        for i in range(self.depth):
            graphs = self.transformers[i].transform(graphs)
        for i in range(self.depth):
            g2 = self.transformers[i].transform(g2)

        if remove_intermediary_layers:
            graphs,g2= self.do_remove_intermediary_layers(graphs,g2)
        return graphs,g2

    def  do_remove_intermediary_layers(self, graphs,g2=[]): # transform and remove intermediary layers
        return map(self.remove_intermediary_layers,graphs),map(self.remove_intermediary_layers , g2)

    def remove_intermediary_layers(self,graph):
        def rabbithole(g, n):
            # wenn base graph dann isses halt n
            if 'original' not in g.graph:
                return [n]

            nodes= g.node[n]['contracted']
            ret=[]
            for no in nodes:
                ret+=rabbithole(g.graph['original'],no)
            return ret

        for n,d in graph.nodes(data=True):
            d['contracted']= rabbithole(graph,n)
        # ok get rid of intermediary things
        supergraph=graph
        while 'original' in graph.graph:
            graph = graph.graph['original']
        supergraph.graph['original']=graph
        return supergraph
