'''
Created on Apr 15, 2016
Evaluate the performance of Top-K recommendation:
    Protocol: leave-1-out evaluation
    Measures: Hit Ratio and NDCG
    (more details are in: Xiangnan He, et al. Fast Matrix Factorization for Online Recommendation with Implicit Feedback. SIGIR'16)

@author: hexiangnan
'''
import math
import heapq # for retrieval topK
import multiprocessing
import numpy as np
from time import time
#from numba import jit, autojit

# Global variables that are shared across processes
_model = None
_testRatings = None
_testNegatives = None
_K = None

def evaluate_model(model, testRatings, testNegatives, K, num_thread):
    """
    Evaluate the performance (Hit_Ratio, NDCG) of top-K recommendation
    Return: score of each test rating.
    """
    global _model
    global _testRatings
    global _testNegatives
    global _K
    _model = model
    _testRatings = testRatings
    _testNegatives = testNegatives
    _K = K
        
    hits, ndcgs = [],[]
    if(num_thread > 1): # Multi-thread
        pool = multiprocessing.Pool(processes=num_thread)
        res = pool.map(eval_one_rating, range(len(_testRatings)))
        pool.close()
        pool.join()
        hits = [r[0] for r in res]
        ndcgs = [r[1] for r in res]
        return (hits, ndcgs)
    # Single thread
    for idx in range(len(_testRatings)):
        (hr,ndcg) = eval_one_rating(idx)
        hits.append(hr)
        ndcgs.append(ndcg)      
    return (hits, ndcgs)

def eval_one_rating(idx):
    rating = _testRatings[idx]
    items = _testNegatives[idx]
    u = rating[0]
    gtItem = rating[1]
    items.append(gtItem)
    # Get prediction scores
    map_item_score = {}
    users = np.full(len(items), u, dtype = 'int32')
    predictions = _model.predict([users, np.array(items)], 
                                 batch_size=100, verbose=0)
    for i in range(len(items)):
        item = items[i]
        map_item_score[item] = predictions[i]
    items.pop()
    
    # Evaluate top rank list
    ranklist = heapq.nlargest(_K, map_item_score, key=map_item_score.get)
    hr = getHitRatio(ranklist, gtItem)
    ndcg = getNDCG(ranklist, gtItem)
    return (hr, ndcg)

def getHitRatio(ranklist, gtItem):
    """
    The function calculates the hit ratio of a given item in a list of ranked items.
    
    :param ranklist: a list of recommended items, ordered by relevance or predicted preference
    :param gtItem: The ground truth item that we are trying to predict whether it appears in the
    ranklist or not
    :return: either 1 or 0, depending on whether the `gtItem` is present in the `ranklist`. If it is
    present, the function returns 1, indicating a hit. If it is not present, the function returns 0,
    indicating a miss.
    """
    for item in ranklist:
        if item == gtItem:
            return 1
    return 0

def getNDCG(ranklist, gtItem):
    """
    The function calculates the normalized discounted cumulative gain (NDCG) of a ranked list of items
    with respect to a ground truth item.
    
    :param ranklist: a list of recommended items in descending order of relevance or preference
    :param gtItem: gtItem is the ground truth item that we are interested in measuring the relevance of
    in the ranking list
    :return: the NDCG (Normalized Discounted Cumulative Gain) score of a given ranklist with respect to
    a ground truth item. If the ground truth item is not present in the ranklist, the function returns
    0.
    """
    for i in range(len(ranklist)):
        item = ranklist[i]
        if item == gtItem:
            return math.log(2) / math.log(i+2)
    return 0
