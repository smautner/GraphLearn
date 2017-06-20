from eden.graph import Vectorizer
from sklearn.metrics.pairwise import cosine_similarity





class simple_directed_estimator():
    def __init__(self, graph=None,vectorizer=Vectorizer(n_jobs=1)):
        self.base = vectorizer.transform([graph])
        self.vectorizer=vectorizer

    def decision_function(self,graphs):
        vgraph= self.vectorizer.transform(graphs)
        return cosine_similarity(self.base,vgraph)