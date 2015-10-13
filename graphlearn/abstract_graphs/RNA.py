from ubergraphlearn import UberWrapper
import eden
import networkx as nx
import subprocess as sp
import forgi
import eden.converter.rna as converter
from eden import path
from sklearn.neighbors import LSHForest
import graphlearn.graph as graphtools
import os
import textwrap

class PreProcessor(object):

    def __init__(self,base_thickness_list=[2]):
        self.base_thickness_list= base_thickness_list

    def fit(self, inputs,vectorizer):
        self.vectorizer=vectorizer
        self.NNmodel=NearestNeighborFolding()
        self.NNmodel.fit(inputs,4)
        return self

    def fit_transform(self,inputs,vectorizer):
        '''
        Parameters
        ----------
        input : many inputs

        Returns
        -------
        graphwrapper iterator
        '''
        inputs=list(inputs)

        self.fit(inputs,vectorizer)
        return self.transform(inputs)

    def re_transform_single(self, graph):
        '''

        Parameters
        ----------
        graphwrapper

        Returns
        -------
        a postprocessed graphwrapper
        '''
        try:
            sequence = get_sequence(graph)
        except:
            from graphlearn.utils import draw
            print 'sequenceproblem:'
            draw.graphlearn(graph, size=20)
            return None

        sequence= sequence.replace("F",'')
        return self.transform([sequence])[0]

    def transform(self,sequences):
        """

        Parameters
        ----------
        sequences : iterable over rna sequences

        Returns
        -------
        list of RnaGraphWrappers
        """
        result=[]
        for sequence in sequences:
            if type(sequence)==str:
                structure = self.NNmodel.transform_single(sequence)
                structure,sequence= fix_structure(structure,sequence)
                base_graph = converter.sequence_dotbracket_to_graph(seq_info=sequence, seq_struct=structure)
                base_graph = self.vectorizer._edge_to_vertex_transform(base_graph)
                base_graph = expanded_rna_graph_to_digraph(base_graph)


                result.append(RnaWrapper(sequence, structure,base_graph, self.vectorizer, self.base_thickness_list))



            # up: normal preprocessing case, down: hack to avoid overwriting the postprocessor
            else:
                result.append(self.re_transform_single(sequence))
        return result






class RnaWrapper(UberWrapper):


    #def core_substitution(self, orig_cip_graph, new_cip_graph):
    #    graph=graphtools.core_substitution( self._base_graph, orig_cip_graph ,new_cip_graph )
    #    return self.__class__( graph, self.vectorizer , self.some_thickness_list)

    def abstract_graph(self):
        '''
        we need to make an abstraction Ooo
        '''
        if self._abstract_graph == None:

            # create the abstract graph and populate the contracted set
            abstract_graph = forgi.get_abstr_graph(self.structure)
            abstract_graph = self.vectorizer._edge_to_vertex_transform(abstract_graph)
            self._abstract_graph = forgi.edge_parent_finder(abstract_graph, self._base_graph)


            #eden is forcing us to set a label and a contracted attribute.. lets do this
            for n, d in self._abstract_graph.nodes(data=True):
                if 'edge' in d:
                    d['label'] = 'e'
            # in the abstract graph , all the edge nodes need to have a contracted attribute.
            # originaly this happens naturally but since we make multiloops into one loop there are some left out
            for n, d in self._abstract_graph.nodes(data=True):
                if 'contracted' not in d:
                    d['contracted'] = set()


        return self._abstract_graph



    def __init__(self,sequence,structure,base_graph,vectorizer=eden.graph.Vectorizer(), base_thickness_list=None,\
                 abstract_graph=None):


        self.some_thickness_list=base_thickness_list
        self.vectorizer=vectorizer
        self._abstract_graph= abstract_graph
        self._base_graph= base_graph
        self.sequence=sequence
        self.structure=structure

        #self._base_graph = converter.sequence_dotbracket_to_graph(seq_info=self.sequence, seq_struct=self.structure)
        #self._base_graph = vectorizer._edge_to_vertex_transform(self._base_graph)
        #self._base_graph = expanded_rna_graph_to_digraph(self._base_graph)

        # normaly anything in the core can be replaced,
        # the mod dict is a way arrounf that rule.. it allows to mark special nodes that can only
        # be replaced by something having the same marker.
        # we dont want start and end nodes to disappear, so we mark them :)
        s,e= get_start_and_end_node(self.base_graph())
        self._mod_dict= {s:696969 , e:123123123}





    def rooted_core_interface_pairs(self, root,thickness = None , **args):
        '''
        we will name the SHARDS of the cip grpahs are not connected
        '''
        ciplist=super(self.__class__, self).rooted_core_interface_pairs( root,thickness, **args)

        '''
        numbering shards if cip graphs not connected
        '''
        for cip in ciplist:
            if not nx.is_weakly_connected(cip.graph):
                comps=[ list(node_list) for node_list in  nx.weakly_connected_components(cip.graph)  ]
                comps.sort()

                for i,nodes in enumerate(comps):

                    for node in nodes:
                        cip.graph.node[node]['shard']=i

        '''
        solve problem of single-ede-nodes in the core
        this may replace the need for fix_structure thing
        this is a little hard.. may fix later

        it isnt hard if i write this code in merge_core in ubergraphlearn

        for cip in ciplist:
            for n,d in cip.graph.nodes(data=True):
                if 'edge' in d and 'interface' not in d:
                    if 'interface' in cip.graph.node[ cip.graph.successors(n)[0]]:
                        #problem found
        '''

        return ciplist



'''
a few handy graph tools :)
'''

def get_sequence(digraph):
    if type(digraph)==str:
        return digraph
    current,end= get_start_and_end_node(digraph)
    seq=digraph.node[current]['label']
    while current != end:
        current = _getsucc(digraph,current)[0][1]
        seq+=digraph.node[current]['label']
    return seq

def _getsucc(graph,root):
    '''
    :param graph:
    :param root:
    :return: [ edge node , nodenode ] along the 'right' path   [edge node, nodenode  ] along the wroong path
    '''
    def post(graph,root):
        p=graph.neighbors(root)
        for e in p:
            yield e, graph.node[e]

    neighbors=post(graph,root)
    retb=[]
    reta=[]

    for node,dict in neighbors:
        if dict['label'] == '-':
            reta.append(node)
            reta+=graph[node].keys()

        if dict['label'] == '=':
            retb.append(node)
            retb+=graph[node].keys()
            retb.remove(root)

    #print 'getsuc',reta, retb,root
    return reta, retb




def get_start_and_end_node(graph):
    # make n the first node of the sequence
    start=-1
    end=-1
    for n,d in graph.nodes_iter(data=True):

        # edge nodes cant be start or end
        if 'edge' in d:
            continue

        # check for start
        if start == -1:
            l= graph.predecessors(n)
            if len(l)==0:
                start = n
            if len(l)==1:
                if graph.node[ l[0] ]['label']=='=':
                    start = n

        # check for end:
        if end == -1:
            l= graph.neighbors(n)
            if len(l)==0:
                end = n
            if len(l)==1:
                if graph.node[ l[0] ]['label']=='=':
                    end = n

    # check and return
    if start==-1 or end==-1:
        raise Exception ('your beautiful "rna" has no clear start or end')
    return start,end


def expanded_rna_graph_to_digraph(graph):
    '''
    :param graph:  an expanded rna representing graph as produced by eden.
                   properties: backbone edges are replaced by a node labeled '-'.
                   rna reading direction is reflected by ascending node ids in the graph.
    :return: a graph, directed edges along the backbone
    '''
    digraph=nx.DiGraph(graph)
    for n,d in digraph.nodes(data=True):
        if 'edge' in d:
            if d['label']=='-':
                ns=digraph.neighbors(n)
                ns.sort()
                digraph.remove_edge(ns[1],n)
                digraph.remove_edge(n,ns[0])
    return digraph


'''
rna feasibility checker
'''
def is_rna (graph):
    graph=graph.copy()
    # remove structure
    bonds= [ n for n,d in graph.nodes(data=True) if d['label']=='=' ]
    graph.remove_nodes_from(bonds)
    # see if we are cyclic
    for node,degree in graph.in_degree_iter( graph.nodes() ):
        if degree == 0:
            break
    else:
        return False
    # check if we are connected.
    graph=nx.Graph(graph)
    return nx.is_connected(graph)



'''
looks for nearest neighbors of a sequence then does multiple alignment
'''
class NearestNeighborFolding(object):


    def fit(self,sequencelist, n_neighbors):
        self.n_neighbors=n_neighbors
        self.sequencelist = sequencelist
        self.vectorizer=path.Vectorizer(nbits=10)
        X=self.vectorizer.transform(self.sequencelist)
        self.neigh =LSHForest()
        self.neigh.fit(X)
        return self



    def get_nearest_sequences(self,sequence):
        needle=self.vectorizer.transform([sequence])
        neighbors=self.neigh.kneighbors(needle,n_neighbors=self.n_neighbors)[1][0].tolist()
        return [ self.sequencelist[i] for i in neighbors  ]



    def transform(self,sequences):
        for seq in sequences:
            yield self.transform_single(seq)

    def transform_single(self, sequence):
        seqs= self.get_nearest_sequences(sequence)
        seqs.append(sequence)
        filename ='./tmp/fold'+str(os.getpid())
        write_fasta(seqs,filename=filename)
        return self.call_folder(filename=filename)

    def call_folder(self,filename='NNTMP'):
        out = sp.check_output('mlocarna %s | grep "HACK%d\|alifold"' % (filename, self.n_neighbors), shell=True)
        out=out.split('\n')
        seq=out[0].split()[1]
        stru=out[1].split()[1]
        stru=list(stru)
        #stru2=''.join(stru)


        # find  deletions
        ids=[]
        for i,c in enumerate(seq):
            if c=='-':
                ids.append(i)



        # take care of deletions

        # remove brackets that dont have a partner anymore
        pairdict=_pairs(stru)
        for i in ids:
            if stru[i]!='.':
                stru[pairdict[i]]='.'

        # delete
        ids.reverse()
        for i in ids:
            del stru[i]
            #stru=stru[:i]+stru[i+1:]

        #print seq
        #print stru2
        #print ''.join(stru)

        return ''.join(stru)


'''
default method if no nearest neighbor folding class is provided
'''

def callRNAshapes(sequence):

    cmd = 'RNAshapes %s' % sequence
    out = sp.check_output(cmd, shell=True)
    s = out.strip().split('\n')

    for li in s[2:]:
        # print li.split()
        energy, shape, abstr = li.split()
        #if abstr == '[[][][]]':
        return shape



'''
these things are used  to  introduce   fake nodes  in graphs... so that we dont see edges in cores anymore
'''
def _pairs(s):
    "give me a bond dict"
    unpaired=[]
    pairs={}
    for i,c in enumerate(s):
        if c=='(':
            unpaired.append(i)
        if c==')':
            partner=unpaired.pop()
            pairs[i]=partner
            pairs[partner]=i
    return pairs

def fix_structure( stru,stri ):
    '''
    the problem is to check every (( and )) .
    if the bonding partners are not next to each other we know that we need to act.
    '''
    p=_pairs(stru)
    lastchar="."
    problems=[]
    for i,c in enumerate(stru):
        # checking for )) and ((
        if c==lastchar and c!='.':
            if abs(p[i]-p[i-1])!=1: #the partners are not next to each other
                problems.append(i)
        # )( provlem
        elif c=='(':
            if lastchar==')':
                problems.append(i)
        lastchar=c

    problems.sort(reverse=True)
    for i in problems:
        stru=stru[:i]+'.'+stru[i:]
        stri=stri[:i]+'F'+stri[i:]

    return stru,stri




'''
Here we see stuff that we use for INFERNAL scores
'''
from graphlearn.graphlearn import GraphLearnSampler
import subprocess  as sp


class UberLearnSampler(GraphLearnSampler):
    def _sample_path_append(self, graph, force=False):
        self._sample_notes+=graph.sequence+"n"
        super(self.__class__,self)._sample_path_append(graph,force=force)


def infernal_checker(sequence_list):
    '''
    :param sequences: a bunch of rna sequences
    :return: get evaluation from cmsearch
    '''
    write_fasta(sequence_list,filename='temp.fa')
    sequence_list = [ s for s in sequence_list if is_sequence(s.replace('F',''))  ]
    #print sequence_list
    return call_cm_search('temp.fa',len(sequence_list))



def is_sequence(seq):
    nuc=["A","U","C","G"] #  :)
    for e in seq:
        if e not in nuc:
            return False
    return len(seq)>5


def write_fasta(sequences,filename='asdasd'):
    fasta=''
    for i,s in enumerate(sequences):
        if len(s) > 5:
            seq=s.replace("F","")
            if not is_sequence(seq):
                continue
            seq='\n'.join(textwrap.wrap(seq, width=60))
            fasta+='>HACK%d\n%s\n\n' % (i,seq)
    with open(filename, 'w') as f:
        f.write(fasta)


def call_cm_search(filename, count):

    out = sp.check_output('./cmsearch -g --noali --incT 0  rf00005.cm %s' % filename, shell=True)
    # -g global
    # --noali, we dont want to see the alignment, score is enough
    # --incT 0 we want to see everything with score > 0
    result={}
    s = out.strip().split('\n')
    for line in s:
        if 'HACK' in line:
            linez=line.split()
            score=float(linez[3])/100
            id = int(linez[5][4:])
            result[id]=score


    return [ result.get(k,0) for k in range(count) ]














