# coding: utf-8

_all_ = [ ]

import os
from pathlib import Path
import sys
parent_dir = os.path.abspath(__file__ + 2 * '/..')
sys.path.insert(0, parent_dir)

from pathlib import Path
import numpy as np
import pandas as pd
import uproot # uproot4
#from itertools import chain

import prod_params
from utils import params

def deltar(df):
    df['deta']=df['cl3d_eta']-df['genpart_exeta']
    df['dphi']=np.abs(df['cl3d_phi']-df['genpart_exphi'])
    sel=df['dphi']>np.pi
    df['dphi']-=sel*(2*np.pi)
    return(np.sqrt(df['dphi']*df['dphi']+df['deta']*df['deta']))
    
def matching(event):
    if event.matches.sum()==0:
        return event.cl3d_pt==event.cl3d_pt.max()
    else:
        cond_a = event.matches==True
        cond_b = event.cl3d_pt==event[cond_a].cl3d_pt.max()
        return (cond_a&cond_b)

def create_dataframes(files, algo_trees, gen_tree, reachedEE):
    print('Input file: {}'.format(files), flush=True)

    # branches_gen = [ 'event', 'genpart_reachedEE', 'genpart_pid', 'genpart_gen',
    #                  'genpart_exphi', 'genpart_exeta', 'genpart_energy' ]
    # branches_cl3d = [ 'event', 'cl3d_energy','cl3d_pt','cl3d_eta','cl3d_phi' ]
    # branches_tc = [ 'event', 'tc_zside', 'tc_energy', 'tc_mipPt', 'tc_pt', 'tc_layer',
    #                 'tc_x', 'tc_y', 'tc_z', 'tc_phi', 'tc_eta', 'tc_id' ]
    branches_gen = [ 'event', 'good_genpart_exphi', 'good_genpart_exeta', 'good_genpart_energy' ]
    branches_cl3d = [ 'event', 'good_cl3d_energy','good_cl3d_pt','good_cl3d_eta','good_cl3d_phi' ]
    branches_tc = [ 'event', 'good_tc_energy', 'good_tc_mipPt', 'good_tc_pt', 'good_tc_layer',
                    'good_tc_x', 'good_tc_y', 'good_tc_z', 'good_tc_phi', 'good_tc_eta' ]
    
    batches_gen, batches_tc = ([] for _ in range(2))
    memsize_gen, memsize_tc = '128 MB', 50000#'64 MB'
    for filename in files:
        with uproot.open(filename + ':' + gen_tree) as data:
            #print( data.num_entries_for(memsize, expressions=branches_tc) )
            for ib,batch in enumerate(data.iterate(branches_gen, step_size=memsize_gen,
                                                   library='pd')):
                batch.set_index('event', inplace=True)

                batches_gen.append(batch)
                print('Step {}: +{} generated data processed.'.format(ib,memsize_gen), flush=True)
                
            for ib,batch in enumerate(data.iterate(branches_tc, step_size=memsize_tc,
                                                   library='pandas')):
                batch = batch[ ~batch['good_tc_layer'].isin(params.disconnectedTriggerLayers) ]
                #convert all the trigger cell hits in each event to a list
                batch = batch.groupby(by=['event']).aggregate(lambda x: list(x))
                batches_tc.append(batch)
                print('Step {}: +{} trigger cells data processed.'.format(ib,memsize_tc), flush=True)

    df_gen = pd.concat(batches_gen)
    df_tc = pd.concat(batches_tc)
    
    df_algos = {}
    assert len(files)==1 #modify the following block otherwise
    for algo_name, algo_tree in algo_trees.items():
        with uproot.open(filename)[algo_tree] as tree:
            df_algos[algo_name] = tree.arrays(branches_cl3d + ['cl3d_layer_pt'], library='pd')
            df_algos[algo_name].reset_index(inplace=True)
            
            # Trick to expand layers pTs, which is a vector of vector
            newcol = df_algos[algo_name].apply(lambda row: row.cl3d_layer_pt[row.subentry], axis=1)
            df_algos[algo_name]['cl3d_layer_pt'] = newcol
            df_algos[algo_name] = df_algos[algo_name].drop(['subentry', 'entry'], axis=1)
            
            # print(list(chain.from_iterable(tree.arrays(['cl3d_layer_pt'])[b'cl3d_layer_pt'].tolist())))
            # new_column = chain.from_iterable(
            #     tree.arrays(['cl3d_layer_pt'])[b'cl3d_layer_pt'].tolist()
            #     )
            # df_algos[algo_name]['cl3d_layer_pt'] = list( new_column )

    return (df_gen, df_algos, df_tc)

def preprocessing():
    files = prod_params.files
    gen, algo, tc = create_dataframes(files,
                                      prod_params.algo_trees, prod_params.gen_tree,
                                      prod_params.reachedEE)

    algo_clean = {}

    for algo_name,df_algo in algo.items():
        #set the indices
        algo_pos.set_index('event', inplace=True)

        #merging gen columns and cluster columns, keeping cluster duplicates (same event)
        algo_pos_merged=gen.join(algo_pos, how='right', rsuffix='_algo').dropna()

        # compute deltar
        algo_pos_merged['deltar']=deltar(algo_pos_merged)

        #could be better:
        algo_pos_merged['matches'] = algo_pos_merged.deltar <= prod_params.threshold

        # matching
        # LP: but then, we want to remove only clusters that aren't "best match"
        #     best match could be:
        #     - Unmatched cluster with highest pT if no dr-matched cluster in evt
        #     - Matched cluster with highest pT *among dr-matched clusters*
        group=algo_pos_merged.groupby('event') # required when dealing with pile-up
        algo_pos_merged['best_match']=group.apply(matching).array

        #keep matched clusters only
        if prod_params.bestmatch_only:
            sel=algo_pos_merged['best_match']==True
            algo_pos_merged=algo_pos_merged[sel]

        algo_clean[algo_name] = algo_pos_merged.sort_values('event')
        algo_clean[algo_name] = algo_clean[algo_name].join(tc, how='left', rsuffix='_tc')

    #save files to savedir in HDF
    store = pd.HDFStore( Path(prod_params.out_dir) / prod_params.out_name, mode='w')
    for algo_name, df in algo_clean.items():
        store[algo_name] = df
    store.close()
        
#Run with: `python scripts/matching_v2.py --cfg scripts.custom_params`
if __name__=='__main__':
    preprocessing()
