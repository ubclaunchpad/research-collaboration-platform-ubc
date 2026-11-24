import numpy as np
import math

class bm25:
    
    def __init__(self, 
                 document_list: list[str],
                 k = 1.25,
                 b = 0.75):
        self.document_list = document_list
        self.documents = []
        self.k = k
        self.b = b
        self.n = len(document_list)
        self.d_avg = 0
        for d in document_list:
            self.documents.append(d.lower().split())
            self.d_avg += len(self.documents[-1])
        self.d_avg = self.d_avg / self.n
        if self.d_avg == 0:
            raise ValueError("There is no word in the documents from databases")
        self.word_df = {}
        self._count()
    
    # probably a numpy 1d array for query_vec
    def vectorized_scores(self, document: str, query_vec: np.ndarray) -> np.ndarray:
        score_metrics = np.zeros(query_vec.shape)
        for i, query in enumerate(query_vec):
            score_metrics[i] = self.score(document=document, query_word=query)
        return score_metrics
    
    
    def score(self, document: str, query_word: str) -> float:
        document = document.lower().split()
        query_word = query_word.lower()
        total_q = 0
        total_w = len(document)
        n = len(self.document_list)
        n_q = self.word_df.get(query_word, 0)

        for w in document:
            if (w == query_word):
                total_q += 1
        
        tf = (total_q * (self.k+1)) / (total_q + self.k * (1 - self.b + self.b * total_w / self.d_avg))
        idf = math.log10((self.n-n_q+0.5)/(n_q+0.5)+1)
        
        return tf * idf
            
    def _count(self):
        for document in self.documents:
            for word in set(document):
                if word not in self.word_df:
                    self.word_df[word] = 1
                else:
                    self.word_df[word] += 1
