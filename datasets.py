""" Module for users datasets """
from typing import List

import pandas as pd
from pc_mongodb import compounds_db, synonyms_db

class DataSet:

    def __init__(self, name: str, compounds: List, activities: List, identifier_type='CID'):
        """  to do  """

        self.name = name
        self.cmps = compounds
        self.activitues = activities
        self.id_type = identifier_type

    def __repr__(self):
        return "{}".format(self.name)

    def __str__(self):
        return self.__repr__()

    def get_cids(self, identifer: str):
        """ converts identifier from the native """

        if self.id_type == 'cid':
            return self.cmps
        elif self.id_type == 'cas':
            return synonyms_db.query_list(self.compounds, 'Synonym', ['CID'])
        elif self.id_type == 'smiles':
            return compounds_db.query_list(self.compounds, 'SMILES Canonical', ['CID'])
        elif self.id_type == 'iupac':
            return compounds_db.query_list(self.compounds, 'IUPAC Name Preferred', ['CID'])




df = pd.read_csv('resources/ER_tutorial/ER_train_can.txt', sep='\t', header=None)



er = DataSet('er', df[0], df[1], identifier_type='SMILES')

