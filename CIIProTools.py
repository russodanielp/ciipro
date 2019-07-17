"""
Module for the tools in the CIIPro tools website at ciipro.rutgers.edu/CIIProTools

Author: Daniel P. Russo

Created: April 4th, 2016 

"""
from BioSimLib import smi_series, getChemSimilarity, act_series_flt, get_chemNN
import pandas as pd

def activity_cliffs(f):
    """ Returns a sorted DataFrame containing Activity Cliff information
    
    f: a file with chemical information
    """
    smi_train = smi_series(f)
    FPs = getFPs(smi_train)
    tan = getChemSimilarity(FPs, FPs)

    NNs = []
    for cid in tan.index:
        # get only the the single nearest neighbor and make sure
        # its not the target compound
        NNs.append(get_chemNN(cid, tan.drop(cid, axis=1), nns=1))

    tmp = pd.concat(NNs)

    NN_df = tmp.reset_index()
    NN_df.index = tan.index
    NN_df.columns = ['NN_CID', 'Similarity']
    
    act = act_series_flt(f)
    
    NN_df['Target_Activity'] = act[NN_df.index].astype('float')
    
    NN_df['NN_Activity'] = act[NN_df.NN_CID].values.astype('float')
    
    NN_df['Cliff'] = abs((NN_df.Target_Activity - NN_df.NN_Activity)).values
    
    NN_df.sort_values(['Cliff', 'Similarity'], ascending=False, inplace=True)
    
    return NN_df

from bokeh.models import ColumnDataSource
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.embed import autoload_static
from bokeh.resources import CDN
def cliffTable_bokeh(cliff):
    """ Returns a JavaScript tag for embedding a Bokeh DataTable on the website. 
    stats: a Pandas DataFrame conatining AID statistical information
    """
    cliff.insert(0, 'Target CID', cliff.index)
    source = ColumnDataSource(cliff)
    columns = [
        TableColumn(field="Target CID", title="Target CID"),
        TableColumn(field="NN_CID", title="NN_CID"),
        TableColumn(field="Similarity", title="Similarity"),
        TableColumn(field="Target_Activity", title="Target_Activity"),
        TableColumn(field="NN_Activity", title="NN_Activity"),           
        TableColumn(field="Cliff", title="Cliff"),
   
            ]
    data_table = DataTable(source=source, columns=columns, editable=False, height=1600, fit_columns=True, row_headers=False)

    js, tag = autoload_static(data_table, CDN, 'static/js/clifftable.js')
    js_file = open('static/js/clifftable.js', 'w')
    js_file.write(js)
    js_file.close()
    return tag
