import pandas as pd
import pymongo
from ciipro_config import CIIProConfig
import os
import logging
import numpy as np

DIR = os.path.dirname(__file__)
log = logging.getLogger(__name__)


def pandas_to_file(df, filename):
    """ Write a file from a Pandas Dataframe.
    
    df: the Pandas DataFrame to be written.
    filename: the directory and filename.
    """
    df.to_csv(filename, sep='\t', index=False)


def file_to_pandas(f):
    """ Reads a file turns a pandas dataframe object
    
    f: a tab deliminated file with column headers
    """
    df = pd.read_table(f, sep='\t')
    df.index = df['CIDS']
    del df.index.name
    df.index = df.index.astype(int)
    return df


def pandas_to_pickle(df, filename):
    """ Write a file from a Pandas Dataframe.

    df: the Pandas DataFrame to be written.
    filename: the directory and filename.
    """
    df.to_pickle(filename)


def pickle_to_pandas(f):
    """ Reads a file turns a pandas dataframe object

    f: a tab deliminated file with column headers
    """
    df = pd.read_pickle(f)
    df.index = [cids[0] for cids in df['CIDS']]
    del df.index.name
    df.Activity = df.Activity.astype(int)
    df.index = df.index.astype(int)
    return df


def getExcel(f):
    """Returns a Pandas ExcelWriter object
        
    f: the filename
    """
    return pd.ExcelWriter(f)

def bioprofile_to_pandas(f):
    """ Reads a file turns a pandas dataframe object
    
    f: a tab deliminated file with CID and bioassay response information.
    """
    df = pd.read_table(f, sep='\t', index_col=False)
    df.index = df.ix[:, 0]
    del df.index.name 
    df.drop(df.columns[0], axis=1, inplace=True)
    #df.astype(int, copy=False)
    df = pd.DataFrame(df.values.astype(int), index=df.index.astype(int), columns=df.columns.astype(int), dtype=int)
    return df


def nn_to_pandas(f):
    df = pd.read_csv(f)
    return df


def remove_duplicate_aids(df):
    """ remove duplicate AIDs from a dataframe while giving preference to active compounds
        remove compounds that are not active or inactive
    """
    log.debug(df)
    #set all cids to the first cid for indexing purposes
    # TODO figure out a better way to do set identifiers
    first_cid = df.loc[0, 'PUBCHEM_CID'].astype(int)
    df['PUBCHEM_CID'] = [first_cid for each in df['PUBCHEM_CID']]
    df = df[df.PUBCHEM_ACTIVITY_OUTCOME.str.contains('Inactive|Active')]
    # sort values by AID than active outcome
    # to be able to keep the first (which would be an active)
    df.sort_values(['PUBCHEM_AID', 'PUBCHEM_ACTIVITY_OUTCOME'], inplace=True)
    df.drop_duplicates(['PUBCHEM_AID'], keep='first', inplace=True)
    return df


def makeBioprofile(df, actives_cutoff=5):
    """ Returns a Pandas DataFrame of CIDS as the index and AIDs as the columns, with bioassays response information as
        values.

        df: A Pandas dataFrame where index are CIDS
        actives_cutoff (int): default=5, number of actives that must be in each PubChem AID
    """
    cids = [cids for cids in df['CIDS']]  # get the cids


    client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)
    client.test.authenticate(CIIProConfig.DB_USERNAME, CIIProConfig.DB_PASSWORD, mechanism='SCRAM-SHA-1')
    db = client.test
    bioassays = db.Bioassays

    row = lambda x: pd.DataFrame(list(bioassays.find({"PUBCHEM_CID": {"$in":x}},
                                            {'PUBCHEM_ACTIVITY_OUTCOME': 1, 'PUBCHEM_AID': 1, 'PUBCHEM_CID': 1,
                                             "_id": 0}
                                            )
                                    )
                                 )

    client.close()


    docs = list(map(row, cids))
    docs = list(filter(lambda df: not df.empty, docs))
    docs = list(map(remove_duplicate_aids, docs))

    df = pd.concat(docs)
    df.columns = ['Activity', 'AID', 'CID']

    df.replace('Inactive', -1, inplace=True)
    df.replace('Active', 1, inplace=True)

    df = df.pivot(index='CID', columns='AID', values='Activity')
    del df.index.name
    del df.columns.name
    df.fillna(0)

    sums = pd.Series(df[df > 0].sum(), index=df.columns)
    m = sums >= actives_cutoff
    df = df.loc[:, m]

    df = df[(df.T != 0).any()]
    return df.fillna(0)


def makeRow(cid, bioassays):
    """Returns responses for a CID as a Pandas DataFrame object with AIDs as index
        
    cid: CID
    bioassays: database name 
    """

    #try:
    docs = pd.DataFrame(list(bioassays.find({"PUBCHEM_CID":cid})))
    if not docs.empty:
        abbrv_docs = docs[['PUBCHEM_ACTIVITY_OUTCOME', 'PUBCHEM_AID']]
        abbrv_docs.columns = ['act', 'aid']
        a1 = abbrv_docs.drop_duplicates(subset='aid')
        a2 = pd.Series(list(a1.act), index=a1.aid, name=cid)
        a2[a2 == 'Inactive'] = -1
        a2[a2 == 'Active'] = 1
        m = (a2 != 1) & (a2 != -1)
        a2[m] = 0
        del a2.index.name
        a2 = pd.Series(a2.values.astype(int), index=a2.index.astype(int), name=cid)
        return  a2
    else:
        return pd.Series()
    #except:
    #    return pd.Series()

def responseMatrix(df, actives_cutoff=5):
    """Returns a Bioprofile as a Pandas DataFrame object for a set of CIDS
    
    df: Pandas DataFrame object where one columns is labeled CIDS and contains compounds to profile
    actives_cutoff (int): default=5, number of actives that must be in each PubChem AID
    """
    # first connect to a database
    client = pymongo.MongoClient("ciipro.rutgers.edu", 27017)
    client.test.authenticate('ciipro', 'ciiprorutgers', mechanism='SCRAM-SHA-1')
    db = client.test
    bioassays = db.Bioassays
    
    # get responses for each cid
    dic = {cid:makeRow(int(cid), bioassays) for cid in df.CIDS}
    # disconnect from db
    client.close()
    
    # concatanate matrix to single Pandas Dataframe object and 
    matrix = pd.concat(dic, axis=1)
    matrix = matrix.T.fillna(0)
    
    # remove AIDS not meeting actives_cutoff
    sums = pd.Series(matrix[matrix > 0].sum(), index=matrix.columns)
    m = sums >= actives_cutoff
    matrix2 = matrix.loc[:, m]
    
    # remove compounds with no responses
    matrix2 = matrix2[(matrix2.T != 0).any()]
    matrix2.drop_duplicates(inplace=True)
    return matrix2


def calcBioSim(mol1, mol2, weight):
    """Returns biosimilarity score and confidence value between two molecules.
    
    mol1: a Pandas series with a vector of AID responses
    mol2: a Pandas series with a vector of AID responses
    weight (float): the weight to apply to inactive values in the calculation
    """
    sim = 0 
    totalAssays = 0 
    for aid in mol1.index:
        if mol1[aid] == mol2[aid]: 
            if mol1[aid] == 0:
                continue
            else:
                if mol1[aid] == 1:
                    sim += 1
                    totalAssays += 1
                elif mol1[aid] == -1:
                    sim += weight
                    totalAssays += weight
                        
        elif mol1[aid] == -(mol2[aid]):
            totalAssays += 1
    if totalAssays == 0:
        return 0.0, 0.0
    else:
        bioSim = sim/totalAssays
        conf = totalAssays
        return float(bioSim), float(conf)


def calcBioSim2(mol1, mol2, weight):
    """Returns biosimilarity score and confidence value between two molecules.
    
    mol1: a Pandas series with a vector of AID responses
    mol2: a Pandas series with a vector of AID responses
    weight (float): the weight to apply to inactive values in the calculation
    """
    
    m_1 = mol1.iloc[mol1.nonzero()[0]]
    m_2 = mol2.iloc[mol2.nonzero()[0]]
    union = (m_1 + m_2).dropna()
    if union.empty:
        return 0.0, 0.0
    
    actives = float(union[union > 0].count()) 
    inactives_weighted = float(union[union < 0].count() * weight)
    disagreements = float(union[union == 0].count())

    conf = actives+inactives_weighted
    biosim = conf/(conf+disagreements)
    return biosim, conf+disagreements

def get_weight(matrix):
    """Return the weight for inactive responses of a matrix
    
    matrix: A Pandas DataFrame object representing a Bioprofile
    """
    pos = pd.Series(matrix[matrix > 0].sum(), index=matrix.columns).sum()
    negs = abs(pd.Series(matrix[matrix < 0].sum(), index=matrix.columns).sum())
    weight = round((pos/(pos + negs))/2, 2)
    return weight



def get_BioSim(train_prof, cids):
    """Returns two Pandas Dataframes for a compound one with biosimilarity scores and the other with the confidence values for that 
        compound with all the compounds in the training dataset.
    
    train_prof: A Pandas DataFrame, containing bioassay response information.
    cids: a Pandas Dataframe where index is cids        
    """  
    # first connect to a database
    client = pymongo.MongoClient("ciipro.rutgers.edu", 27017)
    client.test.authenticate('ciipro', 'ciiprorutgers', mechanism='SCRAM-SHA-1')
    db = client.test
    bioassays = db.Bioassays
    
    
    biosim_matrix = pd.DataFrame(index=cids.index, columns=train_prof.index).fillna(0)
    conf_matrix = pd.DataFrame(index=cids.index, columns=train_prof.index).fillna(0)
    
    weight = get_weight(train_prof)
    print(weight)
    test_prof = makeBioprofile(cids, actives_cutoff=0)

    for cid in test_prof.index:
        test_cmp = test_prof.loc[cid]
        if any(test_cmp != 0):
            for train_cid in train_prof.index:
                biosim, conf = calcBioSim2(test_cmp, train_prof.loc[train_cid], weight=weight)
                biosim_matrix.loc[cid, train_cid] = biosim
                conf_matrix.loc[cid, train_cid] = conf
        else:
            biosim_matrix.loc[cid, :] = [0*len(train_prof.index)]
            conf_matrix.loc[cid, :] = [0*len(train_prof.index)]
    return biosim_matrix, conf_matrix
                

def createNN(biosim_matrix, conf_matrix, bio_sim=0.5, conf_cutoff=4):
    """Returns a dictionary where keys are CIDS in test set and values are Pandas DataFrames with NNs
    
    biosim_matrix: Pandas DataFrame object containing biosimilarity scores
    conf_matrix: Pandas DataFrame object containing confidence values
    bio_sim (float): Default=0.5, Minimum biosimilarity score for NNs
    conf_cutoff (int): Default=4, Minimum biosimilarity values for NNs
    """
    NNs= {}
    for test_comp in biosim_matrix.index:
        biosim = pd.DataFrame(biosim_matrix.loc[test_comp, :].values, index=biosim_matrix.loc[test_comp, :].index)
        conf = pd.DataFrame(conf_matrix.loc[test_comp, :].values, index=conf_matrix.loc[test_comp, :].index)
        df = pd.concat([biosim, conf], axis=1)
        df.columns = ['BioSimilarity', 'Confidence']
        df = getbioNN(df, bio_sim, conf_cutoff)
        NNs[test_comp] = df
    return NNs


def getbioNN(df, cutoff, conf):
    """Returns dictionary where keys are CIDS in test set and values are Pandas DataFrames with NNs
    
    df: Pandas DataFrame object that contains NN information
    cutoff (float): Minimum biosimilarity score for NNs
    conf (int): Minimum biosimilarity values for NNs
    """  
    m = df['BioSimilarity'] > cutoff
    df = df[m]
    m = df['Confidence'] > conf
    df = df[m]
    df.sort_values(['BioSimilarity', 'Confidence'], axis=0, inplace=True, ascending=False)
    df['BioNN'] = df.index
    df.index = range(len(df))
    return df

def get_chemNN(cid, tanimoto, nns=5):
    """ Returns a Pandas Series with chemical top chemical nearest neighbors
    
    cid (int): a PubChem CID
    tanimoto: a Pandas DataFrame object with test CIDS as index and train CIDS as columns, values are tanimoto coefficients
    nns (int): default, 5.  Number of chemical nearest neighbors to cutoff
    """
    sort = tanimoto.loc[cid, :].sort_values(ascending=False, inplace=False)[:nns]
    s = pd.Series(sort, index=sort.index)
    return s

def add_ChemNN(df, s):
    """ Returns df modified with chemical nearest neighbors and correspondind coefficients added
    
    df: A Pandas DataFrame containing NN information
    s: A Pandas Series containing chemical NN information
    """
    df_s = pd.DataFrame(s.index, columns=['ChemNN'])
    df_s['Tanimoto'] = list(s.values)
    df_merg = pd.concat([df, df_s], axis=1)
    return df_merg

def add_BioNN_act(df, act):
    """ Returns df modified to add activity to BioNN
    
    df: Pandas DataFrame containing NN information
    act: Pandas Series containing activity information
    """
    activities = []

    for NN in df.BioNN.dropna():
        activities.append(act[NN])
    df2 = pd.DataFrame(activities, index=range(len(activities)), columns=['BioNN_Activity'])
    df_merg = pd.concat([df, df2], axis=1)
    return df_merg

def add_ChemNN_act(df, act):
    """ Returns df modified to add activity to BioNN
    
    df: Pandas DataFrame containing NN information
    act: Pandas Series containing activity information
    """
    activities = []
    for NN in df.ChemNN.dropna():
        activities.append(act[NN])
    df2 = pd.DataFrame(activities, index=range(len(activities)),  columns=['ChemNN_Activity'])
    df_merg = pd.concat([df, df2], axis=1)
    return df_merg    

def make_BioNN_pred(df, nns):
    """Returns a prediction by merging the activities of the BioNNs
    
    df: Pandas DataFrame containing NN information
    nns (int): Number of nearest neighbors to use for prediction
    """
    if len(df.BioNN_Activity) < nns:
        s = df.BioNN_Activity.sum()
        return s/float(len(df.BioNN_Activity))
    else:
        s = df.BioNN_Activity[:nns].sum()
        return s/float(nns)

def make_ChemNN_pred(df, nns):
    """Returns a prediction by merging the activities of the ChemNNs
    
    df: Pandas DataFrame containing NN information
    nns (int): Number of nearest neighbors to use for prediction
    """
    s = df.ChemNN_Activity[:nns].sum()
    return s/float(nns)


def act_series(f):
    """ Returns Pandas Series of activities Indexed by CIDS
    
    f: file containing CIDS and Activity information
    """
    df = pickle_to_pandas(f)
    series = pd.Series(list(df.Activity.astype(int)), index=df.index)
    return series

def act_series_flt(f):
    """ Returns Pandas Series of activities Indexed by CIDS
    
    f: file containing CIDS and Activity information
    """
    df = pickle_to_pandas(f)
    series = pd.Series(list(df.Activity.astype('float')), index=df.index)
    return series

def smi_series(f):
    """ Returns Pandas Series of SMILES Indexed by CIDS
    
    f: file containing CIDS and Activity information
    """
    df = pickle_to_pandas(f)
    series = pd.Series(list(df.SMILES.astype(str)), index=df.index)
    return series

def match_CIDS_smiles(df, s):
    """ Returns a Pandas series with containing CIDS in bioprofile as index and smiles as values.
    
    df: A Pandas DataFrame containing bioprofile information.
    s: A Pandas Series with CIDS as index and smiles as values.  
    """
    smiles = []
    for CID in df.index:
        smiles.append(s[CID])
    series = pd.Series(smiles, index=df.index)    
    return series

def getSENS(TP, FN):
    """
    Returns sensitivity as defined by True Positives/(True Positive + False Negatives)
    
    TP (int): Number of True Positives.
    FN (int): Number of False Negatives.
    """
    if TP == 0 and FN == 0:
        return 0.0
    else:
        sens = TP/(TP+FN)
        return sens

def getSPEC(TN, FP):
    """ Returns specificity as defined by True Negatives/(True Negatives + False Positives)
    
    TN (int): Number of True Negatives.
    FP (int): Number of False Positives.
    """
    if TN == 0 and FP == 0:
        return 0.0
    else:
        spec = TN/(TN+FP)
        return spec


def getPPV(TP, FP):
    """ Returns positive predictive value as defined by True Positives/(True Positives + False Positives)
    
    TP (int): Number of True Positives.
    FP (int): Number of False Positives.
    """
    if TP == 0 and FP == 0:
        return 0.0
    else:
        PPV = TP/(TP+FP)
        return PPV

def getNPV(TN, FN):
    """ Returns negative predictive value as defined by True Negative/(True Negative + False Negatives)
    
    TN (int): Number of True Negatives.
    FN (int): Number of False Negatives.
    """
    if TN == 0 and FN == 0:
        return 0.0
    else:
        NPV = TN/(TN+FN)
        return NPV
        
def getL(TP, TN, FP, FN):
    """ Returns the L parameter as defined by:
        (True Positives/(True Positives + False Negatives)) * (False Positives + True Negatives/(False Positives + 1))
    
    Note: (True Positives/(True Positives + False Negatives)) is sensitivity.
    
    TP (int): Number of True Positives.
    TN (int): Number of True Negatives.
    FP (int): Number of False Positives.
    FN (int): Number of False Negatives.
    """
    f1 = getSENS(TP, FN)
    f2 = ((FP+TN)/(FP+1.0))
    L = f1*f2
    return L

def getClasses(act, aid):
    """ Returns the number of True Positives, True Negatives, False Positives, and False Negatives for a bioassay.
    
    act: A Pandas Series with activity classfications for PubChem CIDs
    aid: A Pandas Series with bioactivity outcomes for CIDs in a particular PubChem AID
    """
    act[act == 0] = -1 # convert all activity responses from zeros to negative ones

    cmps = aid[((aid == 1) | (aid == -1))].index

    union = (act[cmps] + aid[cmps])

    TP = union[union > 0].count()
    TN = union[union < 0].count()
    
    FP = FN = 0
    
    for cid in union[union == 0].index:
        #print(cid, act[cid])
        if act[cid] == 1:
            FN += 1
        else:
            FP += 1
    
    return map(float, (TP, TN, FP, FN))

def getIVIC(act, df):
    """ Returns a Pandas Dataframe of PubChem AIDs as ows and in vitro, in vivo correlations as columns.
           
    
    act: a Pandas Series containing activity information
    df: a Pandas DataFrame with Bioassay response information
    sortby (str): Default: 'CCR'. Column to sort in vitro, in vivo correlations by. 
    """
    columns = ['TP', 'TN', 'FP', 'FN', 'Sensitivity', 'Specificity', 'CCR', 'PPV', 'NPV', 'L parameter', 'Coverage']
    aid_stats = pd.DataFrame(index=df.columns, columns=columns )
    for aid in df:
        TP, TN, FP, FN = getClasses(act, df[aid])
        sens = getSENS(TP, FN)
        spec = getSPEC(TN, FP)
        ccr = (sens + spec)/2
        ppv = getPPV(TP, FP)
        npv = getNPV(TN, FN)
        l_parameter = getL(TP, TN, FP, FN)
        cov = (TP + TN + FP + FN)/len(df)
        L = [TP, TN, FP, FN, sens, spec, ccr, ppv, npv, l_parameter, cov]
        L[:4] = map(int, L[:4])
        L[4:] = [round(stat, 2) for stat in L[4:]]
        aid_stats.loc[aid, :] = L
    return aid_stats.sort_index()


import urllib.parse, urllib.request, urllib.error
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/"


def getSMILESfromCID(CID):
    """ Returns a smiles string
    
    CID: a PubChem CID
    """
    log.debug("Processing CID for {0}".format(CID))
    url = PUBCHEM_BASE + 'compound/cid/{0}/property/CanonicalSMILES/TXT'.format(CID)
    print(url)
    log.debug("Url is {0}".format(url))
    try:
        response = urllib.request.urlopen(url)
        smiles = response.readline().strip().decode('utf-8')
    except urllib.error.HTTPError as err:
        smiles = np.nan
    except urllib.error.URLError as err:
        smiles = np.nan
    except TimeoutError:
        smiles = np.nan
    print(smiles)
    return smiles





def ifCas(compound):
    """ Returns List of CIDS
    compound (str): A Cas registery number or common name identifier
    """
    try:
        url = PUBCHEM_BASE+"compound/name/"+compound+"/cids/TXT"
        response = urllib.request.urlopen(url)
        for line in response:
            CIDS = line.strip().split()
            CIDS = [x.decode('utf-8') for x in CIDS]
        return CIDS
    except:
        return [None]

def ifSmiles(smiles):
    """ Returns List of CIDS
    
    compound (str): A smiles string
    """
    log.debug("Processing CID for {0}".format(smiles))
    url = PUBCHEM_BASE + 'compound/smiles/' + urllib.parse.quote(smiles) + '/cids/TXT'
    log.debug("Url is {0}".format(url))
    try:
        response = urllib.request.urlopen(url)
        cids = [int(cid.strip()) for cid in response]
    except urllib.error.HTTPError as err:
        print(err)
        cids = np.nan
    except urllib.error.URLError as err:
        print(err)
        cids = np.nan
    except TimeoutError:
        print('timeout')
        cids = np.nan
    return cids

def ifInChIKey(compound):
    """ Returns List of CIDS
    
    compound (str): A InChIKey string
    """
    try:
        url = PUBCHEM_BASE+"compound/inchikey/"+compound+"/cids/TXT"
        response = urllib.request.urlopen(url)
        for line in response:
            CIDS = line.strip().split()
            CIDS = [x.decode('utf-8') for x in CIDS]
        return CIDS
    except:
        return [None]


def convert(compounds, input_type):
    """ Returns a list where elemnts are CIDS for compounds that could be converted or N/A for compounds that could not.
    
    compounds: a list of compounds in string format
    input_type (str): type of chemical identifer 
    """
    CIDS = []
    if input_type == 'CAS' or input_type == 'name':
        for compound in compounds:

            cid = ifCas(compound)
            CIDS.append(cid)


    if input_type == 'smiles':
        for compound in compounds:

            cid = ifSmiles(compound)
            CIDS.append(cid)


    if input_type == 'inchikey':
        for compound in compounds:

            cid = ifInChIKey(compound)
            CIDS.append(cid)

    return CIDS

def convert_file(f, compound_type):
    """ Write a file into the correct format for the website.  Converts different identifiers into PubChem CIDS and obtains SMILES
    
    f: A file containing
    compound_type (str): acceptable input: CAS, name, smiles, inchikey
    """
    if compound_type == 'CID':
        df = pd.read_table(f, dtype=str, header=None, sep='\t')
        df.columns = ['CIDS', 'Activity']
        duplicate_CIDS = df.duplicated(['CIDS'])
        df.drop_duplicates(subset=['CIDS'], inplace=True)
        smiles = [getSMILESfromCID(c)[0] for c in df.CIDS]
        df['SMILES'] = smiles
        df.to_csv(f[:-4] + '_CIIPro.txt', sep='\t', index=False)
        df.to_pickle(f[:-4])
    else:
        df = pd.read_table(f, dtype=str, header=None, sep='\t')
        df.columns = ['Native', 'Activity']
        duplicate_natives = df.duplicated(['Native'])
        CIDS = convert(list(df.Native), compound_type)
        df['CIDS'] = CIDS
        df.dropna(subset=['CIDS'], inplace=True)
        #duplicate_CIDS = df.duplicated(['CIDS'])

        # copy compounds with no CIDS to a list
        # no_cids = list(df['Native'][df['CIDS'] == 'N/A'])
        #df.drop_duplicates(subset=['CIDS'], inplace=True)
        # get smiles 
        smiles = [getSMILESfromCID(c[0]) for c in df.CIDS]
        df['SMILES'] = list(smiles)
        # remove compounds with no CIDS
        df.dropna(subset=['CIDS'], inplace=True)
        df.to_csv(f[:-4] + '_CIIPro.txt', sep='\t', index=False)
        df.to_pickle(f[:-4])






def getChemSimilarity(train_fp, test_fp):
    """ Returns a Pandas DataFrame index are test compounds and columns are test compounds, values are tanimoto coefficients.
    
    train_fp: A dictionary with training CIDS as keys, RDKit MACCS fingerprints as values
    test_fp: A dictionary with test CIDS as keys, RDKit MACCS fingerprints as values
    """
    tanimoto_matrix = pd.DataFrame(index=test_fp.keys(), columns=train_fp.keys())
    for test in test_fp.keys():
        for train in train_fp.keys():
            if train_fp[train] == None or test_fp[test] == None:
                tanimoto_matrix.loc[test, train] = 0.0
            else:
                tanimoto_matrix.loc[test, train] = DataStructs.FingerprintSimilarity(test_fp[test], train_fp[train], metric=DataStructs.TanimotoSimilarity)
    return tanimoto_matrix





def bokehHeatmap(df):
    """ Returns a javascript tag to generate a Bokeh Heatmap.
    
    df: A Pandas DataFrame object.
    """
    from bokeh.models.sources import ColumnDataSource
    from bokeh.models import HoverTool, ResizeTool
    from bokeh.resources import CDN
    from bokeh.embed import autoload_static
    from bokeh.plotting import figure
    import numpy as np
    import pandas as pd

    cmps = []
    assays = []
    xs = []
    ys = []
    acts = []
    colors = []
    toxicity = []

    color_map = {1: 'red', 0: 'white', -1: 'green'}

    for i, cmp in enumerate(df.index):
        cmps = cmps + [str(cmp)] * len(df.columns)
        assays = assays + df.columns.tolist()
        xs = xs + list(np.arange(0.5, len(df.columns) + 0.5))
        ys = ys + [i + 0.5] * len(df.columns)
        acts = acts + [df.iloc[i, a] for a in range(len(df.columns))]
        colors = colors + [color_map[df.iloc[i, a]] for a in range(len(df.columns))]
        #toxicity = toxicity + [df.loc[df.index[i], 'Activity']] * len(df.columns)

    data = pd.DataFrame(dict(
        cmps=cmps,
        assays=assays,
        xs=xs,
        ys=ys,
        acts=acts,
        colors=colors,
        #toxicity=toxicity
    ))

    # data.loc[data.toxicity > 0.75, 'Activity'] = 'Toxic'
    # data.loc[data.toxicity < 0.25, 'Activity'] = 'Not Toxic'
    # data.loc[(data.toxicity >= 0.25) & (data.toxicity <= 0.75), 'Activity'] = 'Marginal'

    d = ColumnDataSource(data)


    height, width = df.shape
    hover = HoverTool()

    hover.tooltips = [
        ("Compound", "@cmps"),
        ("BioAssay", "@assays"),
        ("BioAssay Activity", "@acts"),
        #("Compound Toxicity", "@Activity")
    ]

    hm = figure(x_range=[0, width],
                y_range=[0, height],
                height=800,
                width=800,
                tools=[hover, ResizeTool()])

    hm.rect(x='xs', y='ys',
            height=1,
            width=1,
            fill_color='colors',
            line_color='black',
            source=d,
            line_alpha=0.2
            )

    hm.yaxis.axis_label = 'Compounds'
    hm.xaxis.axis_label = 'BioAssays'
    hm.axis.major_tick_line_color = None
    hm.axis.minor_tick_line_color = None
    hm.axis.major_label_text_color = None
    hm.logo = None
    js, tag = autoload_static(hm, CDN, 'static/js/heatmap.js')
    js_file = open(os.path.join(DIR, 'static/js/heatmap.js'), 'w')
    js_file.write(js)
    js_file.close()
    return tag

def getCoords(angle, biosim):
   
    import math
    lil_angle = math.radians(angle)
    big_angle = math.radians(90-angle)
    length = 1.5 + (1-biosim)*10
    line_start_1 = math.cos(lil_angle)*0.5
    line_start_2 = math.cos(big_angle)*0.5
    line_end_1 = math.cos(lil_angle)*length
    line_end_2 = math.cos(big_angle)*length
    circ_1 = math.cos(lil_angle)*(length+0.5)
    circ_2 = math.cos(big_angle)*(length+0.5)
    return line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2

def createSimilarityGraph(target, df, NNs):
    """Returns a Chemical and Biological Nearest Neighbor graph 
    
    target: an integer, the PubChem ID of the target compound
    df: a Pandas Dataframe containg BioSimilarityilarityilarity and chemical similarity information
    NNs: the number of nearest neighbors used to make predictions
    """
    # color dictionary
    from bokeh.plotting import figure
    from bokeh.resources import CDN
    from bokeh.embed import autoload_static

    activity_color = {
                    1:'#b30000',
                    0:'#228B22', 
                    0.5:'#9a9a9a'
                    }
    
    # first create a figure

    f = figure(
                x_range = (-7.5,7.5),
                y_range = (-7.5,7.5),
                height= 800,
                width= 800, 
                title="PubChem CID " + str(target),
                tools = "save"
                )
    radius = 0.5
    
    # create the background labels
    f.text(-6.5, 6.5, ['Biological Nearest Neighbors'], text_font_size='16pt')
    f.text(6.5, 6.5, ['Chemical Nearest Neighbors'], text_font_size='16pt', text_align='right')
    f.text(0, -7.3, ['Similarity'], text_font_size='10pt', text_align='center')

    
    # create legend
    f.circle(10, 10, legend='Active', radius=radius, fill_color=activity_color[1], 
              color=activity_color[1], alpha=0.8)

    f.circle(10, 10, legend='Inconclusive', radius=radius, fill_color=activity_color[0.5], 
              color=activity_color[0.5], alpha=0.8)
    
    f.circle(10, 10, legend='Inactive', radius=radius, fill_color=activity_color[0], 
              color=activity_color[0], alpha=0.8)


    

    f.annulus(0, 0, inner_radius=0.5, outer_radius=1.5, color="#9a9a9a", alpha=0.8, line_color='#6FA5FF')
    f.annulus(0, 0, inner_radius=1.5, outer_radius=2.5, color="#a7a7a7", alpha=0.8, line_color='#6FA5FF')
    f.annulus(0, 0, inner_radius=2.5, outer_radius=3.5, color="#b3b3b3", alpha=0.8, line_color='#6FA5FF')
    f.annulus(0, 0, inner_radius=3.5, outer_radius=4.5, color="#cdcdcd", alpha=0.8, line_color='#6FA5FF')
    f.annulus(0, 0, inner_radius=4.5, outer_radius=5.5, color="#dadada", alpha=0.8, line_color='#6FA5FF')
    f.annulus(0, 0, inner_radius=5.5, outer_radius=6.5, color="#e6e6e6", alpha=0.8, line_color='#6FA5FF')
    f.line([0, 0,], [-7, 7], line_dash=[6, 3], alpha=0.5)
    
    f.text(0, 1.5,['1.0'], text_font_size='8pt', text_align='center')
    f.text(0, 2.5,['0.9'], text_font_size='8pt', text_align='center')    
    f.text(0, 3.5,['0.8'], text_font_size='8pt', text_align='center')    
    f.text(0, 4.5,['0.7'], text_font_size='8pt', text_align='center')    
    f.text(0, 5.5,['0.6'], text_font_size='8pt', text_align='center')    
    f.text(0, 6.5,['0.5'], text_font_size='8pt', text_align='center')

    # plot the biologcial nearest neighbors
    if len(df.BioNN) < NNs:
        NNs = len(df.BioNN)
    
    if NNs == 1:
        f.line([-0.5, -((1-df.BioSimilarity[0])*10+1.5)], [0, 0], line_color=activity_color[df.BioNN_Activity[0]], alpha=0.8)
        f.circle(-((1-df.BioSimilarity[0])*10+2), 0, radius=radius, fill_color=activity_color[df.BioNN_Activity[0]], 
                      color=activity_color[df.BioNN_Activity[0]], alpha=0.8)       
        f.text(-((1-df.BioSimilarity[0])*10+2), 0, [str(df.BioNN[0])], 
               text_font_size='8pt', text_align='center', text_color='white')   
    
    else:
        for i in range(NNs//2):
            angle = 90/((NNs//2)+1)
            if i == 0:
                line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])
                
                f.line([-line_start_1, -line_end_1], [line_start_2, line_end_2], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                f.circle([-circ_1], [circ_2], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                          color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                f.text([-circ_1], [circ_2], [str(df.BioNN[i])], text_font_size='8pt', 
                            text_align='center', text_color='white')
            else:
                line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])
                
                f.line([-line_start_2, -line_end_2], [line_start_1, line_end_1], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                f.circle([-circ_2], [circ_1], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                          color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                f.text([-circ_2], [circ_1], [str(df.BioNN[i])], text_font_size='8pt', 
                            text_align='center', text_color='white')
            
        if (NNs) % 2 != 0:
            i = NNs//2
            f.line([-0.5, -((1-df.BioSimilarity[i])*10+1.5)], [0, 0], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
            f.circle(-((1-df.BioSimilarity[i])*10+2), 0, radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                      color=activity_color[df.BioNN_Activity[i]], alpha=0.8)       
            f.text(-((1-df.BioSimilarity[i])*10+2), 0, [str(df.BioNN[i])], 
               text_font_size='8pt', text_align='center', text_color='white')
        
            for i in range((NNs//2)+1, NNs):
                if i == (NNs//2)+1:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])
                
                    f.line([-line_start_1, -line_end_1], [-line_start_2, -line_end_2], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.circle([-circ_1], [-circ_2], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                              color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.text([-circ_1], [-circ_2], [str(df.BioNN[i])], text_font_size='8pt', 
                                text_align='center', text_color='white')
                else:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])
                
                    f.line([-line_start_2, -line_end_2], [-line_start_1, -line_end_1], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.circle([-circ_2], [-circ_1], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                              color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.text([-circ_2], [-circ_1], [str(df.BioNN[i])], text_font_size='8pt', 
                            text_align='center', text_color='white')
            
        else:
            for i in range((NNs//2), NNs):
                if i == (NNs//2):
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])

                    f.line([-line_start_1, -line_end_1], [-line_start_2, -line_end_2], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.circle([-circ_1], [-circ_2], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                                  color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.text([-circ_1], [-circ_2], [str(df.BioNN[i])], text_font_size='8pt', 
                                    text_align='center', text_color='white')
                else:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.BioSimilarity[i])

                    f.line([-line_start_2, -line_end_2], [-line_start_1, -line_end_1], line_color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.circle([-circ_2], [-circ_1], radius=radius, fill_color=activity_color[df.BioNN_Activity[i]], 
                                  color=activity_color[df.BioNN_Activity[i]], alpha=0.8)
                    f.text([-circ_2], [-circ_1], [str(df.BioNN[i])], text_font_size='8pt', 
                                text_align='center', text_color='white')
        
        # plot the chemical nearest neighbors
        
    if NNs == 1:
        f.line([0.5, ((1-df.Tanimoto[0])*10+1.5)], [0, 0], line_color=activity_color[df.ChemNN_Activity[0]], alpha=0.8)
        f.circle(((1-df.Tanimoto[0])*10+2), 0, radius=radius, fill_color=activity_color[df.ChemNN_Activity[0]], 
                          color=activity_color[df.ChemNN_Activity[0]], alpha=0.8)       
        f.text(((1-df.Tanimoto[0])*10+2), 0, [str(df.ChemNN[0])], 
                 text_font_size='8pt', text_align='center', text_color='white')   

    else:
        for i in range(NNs//2):
            angle = 90/((NNs//2)+1)
            if i == 0:
                line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                f.line([line_start_2, line_end_2], [line_start_1, line_end_1], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                f.circle([circ_2], [circ_1], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                              color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                f.text([circ_2], [circ_1], [str(df.ChemNN[i])], text_font_size='8pt', 
                                text_align='center', text_color='white')
                    
            else:
                line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                f.line([line_start_1, line_end_1], [line_start_2, line_end_2], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                f.circle([circ_1], [circ_2], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                              color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                f.text([circ_1], [circ_2], [str(df.ChemNN[i])], text_font_size='8pt', 
                                text_align='center', text_color='white')


        if (NNs) % 2 != 0:
            i = NNs//2
            f.line([0.5, ((1-df.Tanimoto[i])*10+1.5)], [0, 0], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
            f.circle(((1-df.Tanimoto[i])*10+2), 0, radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                          color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)       
            f.text(((1-df.Tanimoto[i])*10+2), 0, [str(df.ChemNN[i])], 
                   text_font_size='8pt', text_align='center', text_color='white')

            for i in range((NNs//2)+1, NNs):
                if i == (NNs//2)+1:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                    f.line([line_start_1, line_end_1], [-line_start_2, -line_end_2], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.circle([circ_1], [-circ_2], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                                  color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.text([circ_1], [-circ_2], [str(df.ChemNN[i])], text_font_size='8pt', 
                                    text_align='center', text_color='white')
                else:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                    f.line([line_start_2, line_end_2], [-line_start_1, -line_end_1], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.circle([circ_2], [-circ_1], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                                  color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.text([circ_2], [-circ_1], [str(df.ChemNN[i])], text_font_size='8pt', 
                                text_align='center', text_color='white')

        else:
            for i in range((NNs//2), NNs):
                if i == (NNs//2):
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                    f.line([line_start_1, line_end_1], [-line_start_2, -line_end_2], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.circle([circ_1], [-circ_2], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                                      color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.text([circ_1], [-circ_2], [str(df.ChemNN[i])], text_font_size='8pt', 
                                        text_align='center', text_color='white')
                else:
                    line_start_1, line_start_2, line_end_1, line_end_2, circ_1, circ_2 = getCoords(angle, df.Tanimoto[i])

                    f.line([line_start_2, line_end_2], [-line_start_1, -line_end_1], line_color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.circle([circ_2], [-circ_1], radius=radius, fill_color=activity_color[df.ChemNN_Activity[i]], 
                                      color=activity_color[df.ChemNN_Activity[i]], alpha=0.8)
                    f.text([circ_2], [-circ_1], [str(df.ChemNN[i])], text_font_size='8pt', 
                                    text_align='center', text_color='white')
    
    
    bio_pred = make_BioNN_pred(df, NNs)
    if bio_pred < 0.5:
        bio_pred = 0
    elif bio_pred > 0.5:
        bio_pred = 1
    else:
        bio_pred = 0.5
        
    chem_pred = make_ChemNN_pred(df, NNs)
    if chem_pred < 0.5:
        chem_pred = 0
    elif chem_pred > 0.5:
        chem_pred = 1
    else:
        chem_pred = 0.5
        
    f.annular_wedge(0, 0, outer_radius=radius, inner_radius=0, fill_color=activity_color[bio_pred], 
                    start_angle=90, end_angle=270, color=activity_color[bio_pred], alpha=0.8, start_angle_units='deg', end_angle_units='deg')
    f.annular_wedge(0, 0, outer_radius=radius, inner_radius=0, fill_color=activity_color[chem_pred], 
                    start_angle=270, end_angle=90, color=activity_color[chem_pred], alpha=0.8, start_angle_units='deg', end_angle_units='deg')
    f.text(0, 0, [str(target)], text_font_size='8pt', text_align='center', text_color='black')
    
    f.axis.minor_tick_in = 0
    f.axis.minor_tick_out = 0
    f.axis.major_tick_in = 0
    f.axis.major_tick_out = 0
    f.axis.major_label_text_color = None
    f.grid.grid_line_color = None
    f.legend.orientation = "bottom_right"
    f.legend.background_fill_color = "#cdcdcd"
    f.legend.background_fill_alpha = 0.8
    f.toolbar_location = "below"
    f.logo = None
    #f.background_fill = "#DAFBFF"
    js, tag = autoload_static(f, CDN, 'static/js/sim.js')
    js_file = open('/nvme0n1/ciipro/vm189_zhu/www_ciipro/live/static/js/sim.js', 'w')
    js_file.write(js)
    js_file.close()
    return tag

def sim_graph(target, NNs, nn_cutoff, max_conf):
    """ Returns a similarity graph for a compound.
    
    nn: PubChem CID of target compound
    NNs: a nearest neighbor dictionary
    nn_cuoff: number of nearest neighbors to confsider
    max_conf: total number of assays in bioprofile
    """
    import numpy as np
    from bokeh.plotting import figure, show, ColumnDataSource
    from bokeh.models import FixedTicker, HoverTool, OpenURL, TapTool, NumeralTickFormatter, CategoricalAxis, FactorRange, Range1d
    from bokeh.models import LinearAxis
    from bokeh.resources import CDN
    from bokeh.embed import autoload_static

    activity_color = {
                    1:'#b30000',
                    0:'#228B22', 
                    0.5:'#9a9a9a'
                    }
    NNs = NNs.loc[:nn_cutoff-1]
    
    NNs['BioNN_Activity'][NNs['BioNN_Activity'] == -1] = 0
    NNs['ChemNN_Activity'][NNs['ChemNN_Activity'] == -1] = 0
    
    # BioNN Circles
    
    #NNs['x'] = [(nn+1)/(nn_cutoff+1) for nn in range(len(NNs))]
    #NNs['y'] = [NNs.loc[nn, 'BioSimilarity']*NNs.loc[nn, 'BioNN_Activity'] for nn in range(len(NNs))]
    #NNs['fill_color'] = [activity_color[NNs.loc[nn, 'BioNN_Activity']] for nn in range(len(NNs))] + \
    #NNs['line_color'] = [activity_color[NNs.loc[nn, 'BioNN_Activity']] for nn in range(len(NNs))]
    #NNs['radius'] = [(NNs.loc[nn, 'Confidence']/max_conf)*0.05 for nn in range(len(NNs))]
    

    data_df = pd.DataFrame()
    
    data_df['x'] = [(nn+1)/(nn_cutoff+1) for nn in range(len(NNs))]*2 + \
                   [-(nn+1)/(nn_cutoff+1) for nn in range(len(NNs))]
 
    data_df['y'] = [NNs.loc[nn, 'BioSimilarity'] for nn in range(len(NNs))]*2 + \
                   [NNs.loc[nn, 'Tanimoto'] for nn in range(len(NNs))]
    
    data_df['fill_color'] = [None for nn in range(len(NNs))] + \
                            [activity_color[NNs.loc[nn, 'BioNN_Activity']] for nn in range(len(NNs))] + \
                            [activity_color[NNs.loc[nn, 'ChemNN_Activity']] for nn in range(len(NNs))]
            
    data_df['line_color'] = ['black' for nn in range(len(NNs))] + \
                            [activity_color[NNs.loc[nn, 'BioNN_Activity']] for nn in range(len(NNs))] + \
                            [activity_color[NNs.loc[nn, 'ChemNN_Activity']] for nn in range(len(NNs))]
            
    data_df['radius'] = [0.05 for nn in range(len(NNs))] + \
                        [(NNs.loc[nn, 'Confidence']/max_conf)*0.05 for nn in range(len(NNs))] + \
                        [0.05 for nn in range(len(NNs))]
            
    data_df['alpha'] =  [1 for nn in range(len(NNs))] + \
                        [(NNs.loc[nn, 'Confidence']/max_conf) for nn in range(len(NNs))] + \
                        [0.5 for nn in range(len(NNs))]
            
    data_df['Similarity'] = [0 for nn in range(len(NNs))] + \
                            [NNs.loc[nn, 'BioSimilarity'] for nn in range(len(NNs))] + \
                            [NNs.loc[nn, 'Tanimoto'] for nn in range(len(NNs))]
            
    data_df['Confidence'] = ['N/A' for nn in range(len(NNs))] + \
                            [NNs.loc[nn, 'Confidence'] for nn in range(len(NNs))] + \
                            ['N/A' for nn in range(len(NNs))]
            
    data_df['Similarity'] = data_df['Similarity'].round(decimals=2)

    data_df['CID'] = ['N/A' for nn in range(len(NNs))] + \
                     [NNs.loc[nn, 'BioNN'] for nn in range(len(NNs))] + \
                     [NNs.loc[nn, 'ChemNN'] for nn in range(len(NNs))]
    
    data_df['NN'] = [i for i in range(1, nn_cutoff+1)]*3
    


    
    outer_rings  = ColumnDataSource(data_df.iloc[:nn_cutoff])
    bio_nn  = ColumnDataSource(data_df.iloc[nn_cutoff:nn_cutoff*2])
    chem_nn = ColumnDataSource(data_df.iloc[nn_cutoff*2:])
    
    nn_label = data_df.iloc[nn_cutoff:]
    nn_label['y'] = nn_label['y']-0.06
    nn_label['NN'] = ["NN " + str(i) for i in range(1, nn_cutoff+1)]*2
    nn_label = ColumnDataSource(nn_label)
    
    f = figure(
                x_range = (-1, 1),
                y_range = (-0.15, 1.1),
                height= 800,
                width= 800, 
                title="PubChem CID " + str(target),
                tools = "save,tap"
                ) 

    # throw away circle for the legend
    
    f.circle(x=[2],
             y=[2],
             fill_color=activity_color[0], 
             line_color=activity_color[0], 
             legend='Inactive'
            )
    f.circle(x=[2],
             y=[2],
             fill_color=activity_color[0.5],
             line_color=activity_color[0.5],
             legend='Inconclusive'
            )
    f.circle(x=[2],
             y=[2],
             fill_color=activity_color[1], 
             line_color=activity_color[1], 
             legend='Active'
            )
    
    f.text(
            x=[0.5],
            y=[1.025],
            text=["Biological Nearest Neighbors"],
            text_align="center"
    )
        
    f.text(
            x=[-0.5],
            y=[1.025],
            text=["Chemical Nearest Neighbors"],
            text_align="center"
    )


    f.text(
            x=[0],
            y=[-0.03],
            text=["Predicted Activity"],
            text_align="center",
            text_baseline="top"
    )

    f.quad(top=[1.03], 
           bottom=[-0.03], 
           left=[-0.05],
           right=[0.05], 
           fill_color=None,
           line_color="black",
           line_alpha=0.2,
           line_dash=[6,4]
    )
    f.line(x=[0, 0],
           y=[0, 1],
           line_color='black',
           line_width=1,
           line_alpha=0.2
    )

    f.line(x=[-0.05, 0.05],
           y=[0, 0],
           line_color='black',
           line_width=1,
           line_alpha=0.2,
           
    )

    f.text(
            x=[-0.06],
            y=[0],
            text=["Inactive"],
            text_align="right",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[0]
    )
    f.text(
            x=[0.06],
            y=[0],
            text=["Inactive"],
            text_align="left",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[0]
    )


    
    f.line(x=[-0.025, 0.025],
           y=[0.25, 0.25],
           line_color='black',
           line_width=1,
           line_alpha=0.2,
           
    )
    
    f.line(x=[-0.05, 0.05],
           y=[0.5, 0.5],
           line_color='black',
           line_width=1,
           line_alpha=0.2
    )
    
    f.text(
            x=[-0.06],
            y=[0.5],
            text=["Inconclusive"],
            text_align="right",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[0.5]
    )
    f.text(
            x=[0.06],
            y=[0.5],
            text=["Inconclusive"],
            text_align="left",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[0.5]
    )

    f.line(x=[-0.025, 0.025],
           y=[0.75, 0.75],
           line_color='black',
           line_width=1,
           line_alpha=0.2,
           
    )
    
    f.line(x=[-0.05, 0.05],
           y=[1, 1],
           line_color='black',
           line_width=1,
           line_alpha=0.2,
           
    )

    f.text(
            x=[-0.06],
            y=[1],
            text=["Active"],
            text_align="right",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[1]
    )
    f.text(
            x=[0.06],
            y=[1],
            text=["Active"],
            text_align="left",
            text_baseline="middle",
            text_font_size="8pt",
            text_alpha=0.5,
            text_color=activity_color[1]
    )


    
# plot the bioNN ------------------------------------------------------------
    
    f.circle('x', 'y', source=outer_rings, 
             fill_color='fill_color', 
             line_color='line_color',
             radius='radius',
             alpha='alpha'
            )
    
    render1 = f.circle('x', 'y', source=bio_nn, 
             fill_color='fill_color', 
             line_color='line_color',
             radius='radius',
             alpha='alpha'
            )
    
    
    
    render2 = f.circle('x', 'y', source=chem_nn, 
             fill_color='fill_color', 
             line_color='line_color',
             radius='radius',
             alpha='alpha'
            )
    
    f.text('x', 'y', source=nn_label, 
            text='NN',
            text_align='center',
            text_baseline='middle',
            )
    
    hover = HoverTool()
    hover.tooltips= [
            ("Nearest Neighbor", "@NN"),
            ("Similarity", "@Similarity"),
            ("Confidence", "@Confidence"),
            ("PubChem CID", "@CID")
        ]
    hover.renderers= [render1, render2]
    f.add_tools(hover)
    
    preds = pd.DataFrame()

    preds['x'] = [0, 0]
    preds['y'] = [NNs.loc[0:nn_cutoff, 'ChemNN_Activity'].mean(), NNs.loc[0:nn_cutoff, 'BioNN_Activity'].mean()]
    
    pred_color = []
    for value in preds['y'].values:
        if value > 0.5:
            pred_color.append('#b30000')
        elif value < 0.5:
            pred_color.append('#228B22')
        else:
            pred_color.append('#9a9a9a')
    
    preds['line_color'] = pred_color
    preds['fill_color'] = pred_color
    preds['start_angle'] = [90, 270]
    preds['end_angle'] = [270, 90]
    preds['radius'] = [0.05, 0.05]
    preds['Prediction'] = [NNs.loc[0:nn_cutoff, 'ChemNN_Activity'].mean(), NNs.loc[0:nn_cutoff, 'BioNN_Activity'].mean()]
    preds['alpha'] = [0.5, 0.5]
    preds = ColumnDataSource(preds)
    
    prediction = f.wedge(
                x='x',
                y='y',
                line_color='line_color',
                fill_color='fill_color',
                start_angle='start_angle',
                start_angle_units='deg',
                end_angle='end_angle',
                end_angle_units='deg',
                radius='radius',
                alpha='alpha',
                source=preds
    )

    hover2 = HoverTool()
    hover2.tooltips= [
            ("Prediction", "@Prediction"),
        ]
    hover2.renderers= [prediction]
    f.add_tools(hover2)

    
    
    url = "https://pubchem.ncbi.nlm.nih.gov/compound/@CID/"
    taptool = f.select(type=TapTool)
    taptool.callback = OpenURL(url=url)
    
    f.extra_y_ranges = {"category": Range1d(start=-0.15, end=1.1)}
    s_axis = LinearAxis(y_range_name="category")
    s_axis.ticker=FixedTicker(ticks=[-1, -0.75, -0.5, -0.25, 0, 0.25, .5, .75, 1])
    f.add_layout(s_axis, 'right')    

    # set axis
    
    f.yaxis[0].ticker=FixedTicker(ticks=[-1, -0.75, -0.5, -0.25, 0, 0.25, .5, .75, 1])
    #f.yaxis[0].formatter = NumeralTickFormatter(format="0.0%")
    #f.yaxis.axis_label = "Similarity"
    #f.ygrid.grid_line_alpha = 0.5
    #f.ygrid.grid_line_dash = [6, 4]
    f.ygrid.grid_line_color = None
    
    f.xaxis.minor_tick_in = 0
    f.xaxis.minor_tick_out = 0
    f.xaxis.major_tick_in = 0
    f.xaxis.major_tick_out = 0
    f.xaxis.major_label_text_color = 'None'
    f.xgrid.grid_line_color = None
    #f.add_layout(f.xaxis, 'right')

    f.legend.orientation = "bottom_right"
    f.legend.background_fill_color = "#cdcdcd"
    f.legend.background_fill_alpha = 0.8
    f.toolbar_location = "below"
    f.logo = None
    #path = os.path.join(DIR, 'static/js/sim.js')
    js, tag = autoload_static(f, CDN, 'static/js/sim.js')
    js_file = open(os.path.join(DIR, 'static/js/sim.js'), 'w')
    js_file.write(js)
    js_file.close()
    return tag


def dataTable_bokeh(stats):
    """ Returns a JavaScript tag for embedding a Bokeh DataTable on the website. 
    stats: a Pandas DataFrame conatining AID statistical information
    """
    from bokeh.models import ColumnDataSource
    from bokeh.models.widgets import DataTable, TableColumn
    from bokeh.embed import autoload_static
    from bokeh.io import vform
    from bokeh.resources import CDN


    stats.insert(0, 'PubChem AID', stats.index)
    source = ColumnDataSource(stats)
    columns = [
        TableColumn(field="PubChem AID", title="PubChem AID"),
        TableColumn(field="TP", title="TP"),
        TableColumn(field="TN", title="TN"),
        TableColumn(field="FP", title="FP"),           
        TableColumn(field="FN", title="FN"),
        TableColumn(field="Sensitivity", title="Sensitivity"),
        TableColumn(field="Specificity", title="Specificity"),
        TableColumn(field="CCR", title="CCR"),
        TableColumn(field="PPV", title="PPV"),
        TableColumn(field="NPV", title="NPV"),
        TableColumn(field="L parameter",   title="L parameter"),  
        TableColumn(field="Coverage", title="Coverage")  
            ]
    data_table = DataTable(source=source, columns=columns,
                           editable=False, height=1600, width=1000, fit_columns=True,
                        row_headers=False)
    js, tag = autoload_static(vform(data_table), CDN, 'static/js/datatable.js')
    js_file = open(os.path.join(DIR, 'static/js/datatable.js'), 'w')
    js_file.write(js)
    js_file.close()
    return tag
