""" just read and writing files """

import json, glob, os
from rdkit import Chem
from typing import List

def parse_upload_file(filename: str):
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