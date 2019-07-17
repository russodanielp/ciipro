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
    # test to see if native index is string or int
    try:
        df.index = df.index.astype(int)
    except TypeError:
        df.index = df.index
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
    # df.astype(int, copy=False)
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
    # set all cids to the first cid for indexing purposes
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
    cids = [int(cid[0]) for cid in df['CIDS']]  # get the cids
    cids = list(map(int, cids))

    client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)
    client.test.authenticate(CIIProConfig.DB_USERNAME, CIIProConfig.DB_PASSWORD, mechanism='SCRAM-SHA-1')
    db = client.test
    bioassays = db.Bioassays

    print(cids)
    df = pd.DataFrame(list(bioassays.find({"PUBCHEM_CID": {"$in": cids}},
                                          {'PUBCHEM_ACTIVITY_OUTCOME': 1, 'PUBCHEM_AID': 1, 'PUBCHEM_CID': 1,
                                           "_id": 0}
                                          )
                           )
                      )

    client.close()

    # df = pd.concat(docs)
    df.columns = ['Activity', 'AID', 'CID']
    # df.drop_duplicates('CID', inplace=True)
    df = df.drop_duplicates(subset=['AID', 'CID'])

    df['Activity'] = [val if val in ['Active', 'Inactive'] else 0 for val in df.Activity]
    df.replace('Inactive', -1, inplace=True)
    df.replace('Active', 1, inplace=True)

    df = df.pivot(index='CID', columns='AID', values='Activity')

    del df.index.name
    del df.columns.name
    df = df.fillna(0)

    sums = (df == 1).sum()

    df = df.loc[:, sums >= actives_cutoff]

    df = df[(df != 0).any(1)]

    return df


def makeRow(cid, bioassays):
    """Returns responses for a CID as a Pandas DataFrame object with AIDs as index

    cid: CID
    bioassays: database name
    """

    # try:
    docs = pd.DataFrame(list(bioassays.find({"PUBCHEM_CID": cid})))
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
        return a2
    else:
        return pd.Series()
    # except:
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
    dic = {cid: makeRow(int(cid), bioassays) for cid in df.CIDS}
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
        bioSim = sim / totalAssays
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

    conf = actives + inactives_weighted
    biosim = conf / (conf + disagreements)
    return biosim, conf + disagreements


def get_weight(matrix):
    """Return the weight for inactive responses of a matrix

    matrix: A Pandas DataFrame object representing a Bioprofile
    """
    pos = pd.Series(matrix[matrix > 0].sum(), index=matrix.columns).sum()
    negs = abs(pd.Series(matrix[matrix < 0].sum(), index=matrix.columns).sum())
    weight = round((pos / (pos + negs)) / 2, 2)
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
            biosim_matrix.loc[cid, :] = [0 * len(train_prof.index)]
            conf_matrix.loc[cid, :] = [0 * len(train_prof.index)]
    return biosim_matrix, conf_matrix


def createNN(biosim_matrix, conf_matrix, bio_sim=0.5, conf_cutoff=4):
    """Returns a dictionary where keys are CIDS in test set and values are Pandas DataFrames with NNs

    biosim_matrix: Pandas DataFrame object containing biosimilarity scores
    conf_matrix: Pandas DataFrame object containing confidence values
    bio_sim (float): Default=0.5, Minimum biosimilarity score for NNs
    conf_cutoff (int): Default=4, Minimum biosimilarity values for NNs
    """
    NNs = {}
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
    df2 = pd.DataFrame(activities, index=range(len(activities)), columns=['ChemNN_Activity'])
    df_merg = pd.concat([df, df2], axis=1)
    return df_merg


def make_BioNN_pred(df, nns):
    """Returns a prediction by merging the activities of the BioNNs

    df: Pandas DataFrame containing NN information
    nns (int): Number of nearest neighbors to use for prediction
    """
    if len(df.BioNN_Activity) < nns:
        s = df.BioNN_Activity.sum()
        return s / float(len(df.BioNN_Activity))
    else:
        s = df.BioNN_Activity[:nns].sum()
        return s / float(nns)


def make_ChemNN_pred(df, nns):
    """Returns a prediction by merging the activities of the ChemNNs

    df: Pandas DataFrame containing NN information
    nns (int): Number of nearest neighbors to use for prediction
    """
    s = df.ChemNN_Activity[:nns].sum()
    return s / float(nns)


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
        sens = TP / (TP + FN)
        return sens


def getSPEC(TN, FP):
    """ Returns specificity as defined by True Negatives/(True Negatives + False Positives)

    TN (int): Number of True Negatives.
    FP (int): Number of False Positives.
    """
    if TN == 0 and FP == 0:
        return 0.0
    else:
        spec = TN / (TN + FP)
        return spec


def getPPV(TP, FP):
    """ Returns positive predictive value as defined by True Positives/(True Positives + False Positives)

    TP (int): Number of True Positives.
    FP (int): Number of False Positives.
    """
    if TP == 0 and FP == 0:
        return 0.0
    else:
        PPV = TP / (TP + FP)
        return PPV


def getNPV(TN, FN):
    """ Returns negative predictive value as defined by True Negative/(True Negative + False Negatives)

    TN (int): Number of True Negatives.
    FN (int): Number of False Negatives.
    """
    if TN == 0 and FN == 0:
        return 0.0
    else:
        NPV = TN / (TN + FN)
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
    f2 = ((FP + TN) / (FP + 1.0))
    L = f1 * f2
    return L


def getClasses(act, aid):
    """ Returns the number of True Positives, True Negatives, False Positives, and False Negatives for a bioassay.

    act: A Pandas Series with activity classfications for PubChem CIDs
    aid: A Pandas Series with bioactivity outcomes for CIDs in a particular PubChem AID
    """
    act[act == 0] = -1  # convert all activity responses from zeros to negative ones
    aid_reduce = aid.iloc[aid.nonzero()[0]]
    u = act.index.intersection(aid_reduce.index)

    union = (act[u] + aid_reduce[u])
    TP = union[union > 0].count()
    TN = union[union < 0].count()

    FP = FN = 0

    for cid in union[union == 0].index:
        # print(cid, act[cid])
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
    aid_stats = pd.DataFrame(index=df.columns, columns=columns)
    for aid in df:
        TP, TN, FP, FN = getClasses(act, df[aid])
        sens = getSENS(TP, FN)
        spec = getSPEC(TN, FP)
        ccr = (sens + spec) / 2
        ppv = getPPV(TP, FP)
        npv = getNPV(TN, FN)
        l_parameter = getL(TP, TN, FP, FN)
        cov = (TP + TN + FP + FN) / len(df)
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
        smiles = [np.nan]
    except urllib.error.URLError as err:
        smiles = [np.nan]
    except TimeoutError:
        smiles = [np.nan]
    print(smiles)
    return smiles


def ifCas(compound):
    """ Returns List of CIDS
    compound (str): A Cas registery number or common name identifier
    """
    try:
        url = PUBCHEM_BASE + "compound/name/" + compound + "/cids/TXT"
        response = urllib.request.urlopen(url)
        for line in response:
            CIDS = line.strip().split()
            CIDS = [int(x.decode('utf-8')) for x in CIDS]
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
        url = PUBCHEM_BASE + "compound/inchikey/" + compound + "/cids/TXT"
        response = urllib.request.urlopen(url)
        for line in response:
            CIDS = line.strip().split()
            CIDS = [x.decode('utf-8') for x in CIDS]
        return CIDS
    except:
        return [None]

# def convert(compounds, input_type):
#     """ Returns a list where elemnts are CIDS for compounds that could be converted or N/A for compounds that could not.
#
#     compounds: a list of compounds in string format
#     input_type (str): type of chemical identifer
#     """
#     CIDS = []
#     if input_type == 'CAS' or input_type == 'name':
#         for compound in compounds:
#
#             cid = ifCas(compound)
#             CIDS.append(cid)
#
#
#     if input_type == 'smiles':
#         for compound in compounds:
#
#             cid = ifSmiles(compound)
#             CIDS.append(cid)
#
#
#     if input_type == 'inchikey':
#         for compound in compounds:
#
#             cid = ifInChIKey(compound)
#             CIDS.append(cid)
#
#     return CIDS
#
# def convert_file(f, compound_type):
#     """ Write a file into the correct format for the website.  Converts different identifiers into PubChem CIDS and obtains SMILES
#
#     f: A file containing
#     compound_type (str): acceptable input: CAS, name, smiles, inchikey
#     """
#     if compound_type == 'CID':
#         df = pd.read_table(f, dtype=str, header=None, sep='\t')
#         df.columns = ['CIDS', 'Activity']
#         duplicate_CIDS = df.duplicated(['CIDS'])
#         df.drop_duplicates(subset=['CIDS'], inplace=True)
#         smiles = [getSMILESfromCID(c)[0] for c in df.CIDS]
#         df['SMILES'] = smiles
#         df.to_csv(f[:-4] + '_CIIPro.txt', sep='\t', index=False)
#         df.to_pickle(f[:-4])
#     else:
#         df = pd.read_table(f, dtype=str, header=None, sep='\t')
#         df.columns = ['Native', 'Activity']
#         duplicate_natives = df.duplicated(['Native'])
#         CIDS = convert(list(df.Native), compound_type)
#         df['CIDS'] = CIDS
#         df.dropna(subset=['CIDS'], inplace=True)
#         #duplicate_CIDS = df.duplicated(['CIDS'])
#
#         # copy compounds with no CIDS to a list
#         # no_cids = list(df['Native'][df['CIDS'] == 'N/A'])
#         #df.drop_duplicates(subset=['CIDS'], inplace=True)
#         # get smiles
#         smiles = [getSMILESfromCID(c[0]) for c in df.CIDS]
#         df['SMILES'] = list(smiles)
#         # remove compounds with no CIDS
#         df.dropna(subset=['CIDS'], inplace=True)
#         df.to_csv(f[:-4] + '_CIIPro.txt', sep='\t', index=False)
#         df.to_pickle(f[:-4])


def convert_names(ids, lookup_id):
    all_cids, all_smiles = [], []
    client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)
    lookup_collection = {'Synonym': client['pubchem']['synonyms'], 'InChIKey Standard': client['pubchem']['compounds']}

    for cpd in ids:
        try:
            cid = lookup_collection[lookup_id].find({lookup_id: cpd})[0]['CID']
            all_cids.append(cid)
            all_smiles.append(client['pubchem']['compounds'].find({'CID': cid})[0]['SMILES Canonical'])

        except:
            all_cids.append([None])
            all_smiles.append([None])

    return all_cids, all_smiles


def convert_cids(ids):
    client = pymongo.MongoClient(CIIProConfig.DB_SITE, 27017)

    return ids, [client['pubchem']['compounds'].find({'CID': cid})[0]['SMILES Canonical'] for cid in ids]


def convert_smiles(ids):
    return [ifSmiles(smiles) for smiles in ids], ids


def convert(ids, idtype):
    lookup_ids = {'CAS': 'Synonym', 'name': 'Synonym', 'inchikey': 'InChIKey Standard'}

    if idtype in lookup_ids.keys():
        return convert_names(ids, lookup_ids[idtype])

    elif idtype is 'smiles':
        return convert_smiles(ids)

    elif idtype is 'CID':
        return convert_cids(ids)





