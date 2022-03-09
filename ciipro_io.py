""" just read and writing files """

import json, glob, os
from rdkit import Chem
from typing import List
import pandas as pd
import typing as tp
from pc_mongodb import compounds_db, outcomes_db


def check_input_file(filename: str) -> tp.Tuple[bool, str]:
    """ checks for validity of an uploaded file and returns a
    tuple of a boolean stating wether its valid and and error message """

    raw_data = pd.read_csv(filename, header=None, sep='\t')

    # check two columns
    if len(raw_data.columns) != 2:
        return False, "Dataset does not contain two columns."

    # check identifiers are unique
    if raw_data[0].duplicated().any():
        return False, "Dataset contains non-unique identifiers."

    # check activity for each molecule
    if raw_data[1].isna().any():
        return False, "Dataset contains missing activity values."

    return True, ""


def convert_upload_data(upload_data: pd.DataFrame, identifier: str) -> pd.DataFrame:
    """ converts uploaded data from a two columns to get smiles, cid, and inchi """
    identifier_list = upload_data[identifier].values.tolist()

    if identifier == 'cid':
        query_field = 'CID'
    elif identifier == 'smiles':
        query_field = 'SMILES Canonical'
    else:
        query_field = 'InChI Standard'


    pipeline = [
        {'$match': {query_field: {'$in': identifier_list}}},
        {'$project': {
            'cid': '$CID',
            'smiles': '$SMILES Canonical',
            'inchi': '$InChI Standard'

        }}
    ]

    df = pd.DataFrame(list(compounds_db.col_ob.aggregate(pipeline)))
    return df


def get_compounds_from_aid(aid: str) -> pd.DataFrame:
    """ given an aid, will get compound information all compounds from that aid along with
     their inchi """


    pipeline = [
        {'$match': {'AID': aid, '$or': [{'Outcome':'Active'}, {'Outcome': 'Inactive'}]}},

        {'$project': {
            'CID': '$CID',
            'AID': '$AID',
            'Activity': '$Outcome',
            '_id': 0
        }},
        # {
        #   '$lookup': {
        #       'from': 'compounds',
        #       'let': {'cid': '$CID', 'ccid': '$compounds.CID'},
        #       'as': 'structure_info',
        #       'pipeline': [
        #           {'$match': { '$expr': {'$eq': [ "$$cid", "$$ccid" ] }}},
        #           {'$project': {'InChI Standard': 1, '_id': 0}}
        #       ]
        #   }
        # }
        {
            '$lookup': {
                'from': 'compounds',
                'localField': 'CID',
                'foreignField': 'CID',
                'as': 'structure_info'

            }
        },
        {'$unwind': "$structure_info"},
        {'$project': {
            'cid': '$CID',
            'activity': '$Activity',
            'inchi': '$structure_info.InChI Standard',
            'smiles': '$structure_info.SMILES Canonical',
            '_id': 0
        }},
    ]

    df = pd.DataFrame(list(outcomes_db.col_ob.aggregate(pipeline)))
    df['activity'] = df['activity'].map({'Active': 1, 'Inactive': 0})
    return df

def pubchem_aid_is_in_db(pubchem_aid: str) -> bool:
    return outcomes_db.col_ob.find({'AID': pubchem_aid}).count() > 0


def parse_upload_file(filename: str) -> pd.DataFrame:
    identifiers = []
    activities = []
    f = open(filename, 'r')

    for line in f:
        line = line.strip()

        identifier = line.split('\t')[0].strip()
        activity = line.split('\t')[1].strip()

        identifiers.append(identifier)
        activities.append(activity)

    return identifiers, activities

def get_all_json_files(dir: str):
    return glob.glob(os.path.join(dir, '*.json'))

def load_json(dir):
    """ simply loads a json dataset """

    with open(dir) as json_file:
        json_data = json.load(json_file)
    return json_data


def get_profiles_names_for_user(profiles_dir: str):

    # TODO: find a better way to not get adj_matrix file
    all_jsons = [json_file for json_file in glob.glob(os.path.join(profiles_dir, '*.json'))
                 if 'adj_matrix' not in json_file]
    names = []

    for json_file in all_jsons:
        profile = load_json(json_file)
        names.append(profile['name'])
    return names

def read_sdf(filename: str) -> List[Chem.Mol]:
    """
    Returns a set of mols, eliminates any unreadable molecules"
    """
    return [m for m in Chem.SDMolSupplier(filename) if m]

def read_curation_txt(filename: str) -> List:
    data = []
    f = open(filename, 'r')
    for line in f:
        line = line.strip()
        data.append(line.split('\t')[0].strip())
    return data

def parse_mols(mols: List[Chem.Mol]) -> List:
    """
        convert an sdfile to a list of list with smiles as the identifier
    """
    headers = ['SMILES']
    for mol in mols:
        for prop in list(mol.GetPropNames()):
            if prop not in headers:
                headers.append(prop)

    data = []
    data.append(headers[:5])

    for mol in mols:
        mol_data = [Chem.MolToSmiles(mol)]
        for header in headers[1:5]:
            if mol.HasProp(header):
                mol_data.append(mol.GetProp(header))
            else:
                mol_data.append('NA')
        data.append(mol_data)
    return data

if __name__ == '__main__':
    # test = pd.read_csv('/Users/danielrusso/data/ciipro_test_sets/ciipro_test.txt', sep='\t', header=None)
    # test[0] = test[0].astype(str)
    # df = convert_upload_data(test.iloc[:20], identifier='cid')
    # print(df.head())
    #print(list(outcomes_db.col_ob.find({'AID': '1'})))
    df = get_compounds_from_aid('1')
    print(df.Activity.value_counts())