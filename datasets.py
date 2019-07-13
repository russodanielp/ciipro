""" Module for users datasets """
from typing import List

import pandas as pd
from pc_mongodb import compounds_db, synonyms_db

class DataSet:

    def __init__(self, name: str, compounds: List, activities: List, identifier_type='CID'):
        """  to do  """

        self.name = name
        self.compounds = compounds
        self.activities = activities
        self.id_type = identifier_type

    def __repr__(self):
        return "{}".format(self.name)

    def __str__(self):
        return self.__repr__()

    def get_cids(self):
        """ converts identifier from the native """

        if self.id_type == 'cid':
            return self.cmps
        elif self.id_type == 'cas':
            return synonyms_db.query_list(self.cmopounds, 'Synonym', ['CID'])
        elif self.id_type == 'smiles':
            return compounds_db.query_list(self.compounds, 'SMILES Canonical', ['CID'])
        elif self.id_type == 'iupac':
            return compounds_db.query_list(self.compounds, 'IUPAC Name Preferred', ['CID'])

    def get_assays(self):
        """  """

def make_dataset(dataset_json):
    """ takes the json of a dataset and makes a dataset object """
    name = dataset_json['overview']['name']
    identifier_type = dataset_json['overview']['identifier_type']
    identifiers = [compound['identifier'] for compound in dataset_json['compounds']]
    activities = [compound['activity'] for compound in dataset_json['compounds']]
    return DataSet(name, identifiers, activities, identifier_type)


df = pd.read_csv('resources/ER_tutorial/ER_test_can.txt', sep='\t', header=None)



er = DataSet('er', df[0].values.tolist(), df[1].values.tolist(), identifier_type='smiles')

