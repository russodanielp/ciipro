""" functions for reading and writing uploaded datasets to json """

import json
from pandas import DataFrame
import pandas as pd
import os, glob
from typing import List

def write_ds_to_json(identifiers: List, activities: List, to_dir: str, name: str, identifier_type: str, set_type='training'):
    """ writes a dataset to a json file.  dataset is a dataframe where the first column is an
     identifier and the second is the corresponding activities

      set_type: training or test
      """

    # the json object will be a list of dictionaries, each dictionary contains
    # compound info

    dataset = {}

    # keep track of meta data for dataset
    no_actives, no_inactives = 0, 0

    compounds = []
    for id, act in zip(identifiers, activities):
        row_dict = {}
        row_dict['identifier'] = id
        row_dict['activity'] = act

        if act == 1:
            no_actives += 1
        elif act == 0:
            no_inactives += 1
        compounds.append(row_dict)

    dataset['compounds'] = compounds

    # get meta data for dataset

    dataset['overview'] = {}
    dataset['overview']['actives'] = no_actives
    dataset['overview']['inactives'] = no_inactives
    dataset['overview']['identifier_type'] = identifier_type
    dataset['overview']['name'] = name
    dataset['overview']['set_type'] = set_type

    to_dir  = os.path.join(to_dir, '{}.json'.format(name))

    with open(to_dir, 'w') as output_file:
        json.dump(dataset, output_file)

def load_json(dir):
    """ simply loads a json dataset """

    with open(dir) as json_file:
        dataset = json.load(json_file)

    return dataset


def get_datasets_names_for_user(compounds_dir: str, set_type='training'):
    all_jsons = glob.glob(os.path.join(compounds_dir, '*.json'))
    names = []

    for json_file in all_jsons:

        dataset = load_json(json_file)

        if dataset['overview']['set_type'] == set_type:
            names.append(dataset['overview']['name'])
    return names
#
# df = pd.read_csv('resources/ER_tutorial/ER_test_can.txt', sep='\t', header=None)
#
# to_dir = 'resources/'
#
# write_ds_to_json(df, to_dir, 'er', 'smiles')

