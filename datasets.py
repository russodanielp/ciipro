""" Module for users datasets """
from typing import List

import pandas as pd
from pc_mongodb import compounds_db, synonyms_db, outcomes_db

import pandas as pd
import numpy as np

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
            return compounds_db.query_list(self.compounds, 'CID', ['CID'])
        elif self.id_type == 'cas':
            return synonyms_db.query_list(self.cmopounds, 'Synonym', ['CID'])
        elif self.id_type == 'smiles':
            return compounds_db.query_list(self.compounds, 'SMILES Canonical', ['CID'])
        elif self.id_type == 'iupac':
            return compounds_db.query_list(self.compounds, 'IUPAC Name Preferred', ['CID'])

    def get_assays(self):
        """ queries the outcomes databases to get assays """

        cids = [cmp['CID'] for cmp in self.get_cids()]
        assays = outcomes_db.query_list(cids, 'CID', ['AID', 'Outcome'])
        return assays

    def get_bioprofile(self):

        assays = self.get_assays()

        # need to convert to numbers for pandas

        assays_conerted = []
        for assay_data in assays:
            if assay_data['Outcome'] == 'Active':
                assay_data['Outcome'] = 1
            elif assay_data['Outcome'] == 'Inactive':
                assay_data['Outcome'] = -1
            else:
                assay_data['Outcome'] = 0


        # the agg funtion should give preferences to activtes
        df = pd.DataFrame(assays).pivot_table(index='CID', columns='AID', values='Outcome', aggfunc=np.max)
        return df.fillna(0)




def make_dataset(dataset_json):
    """ takes the json of a dataset and makes a dataset object """
    name = dataset_json['overview']['name']
    identifier_type = dataset_json['overview']['identifier_type']
    identifiers = [compound['identifier'] for compound in dataset_json['compounds']]
    activities = [compound['activity'] for compound in dataset_json['compounds']]
    return DataSet(name, identifiers, activities, identifier_type)


if __name__ == '__main__':
    import datasets_io

    json_data = datasets_io.load_json(r'D:\ciipro\Guest\datasets\Carc_epoxides_aziridines.json')
    ds = make_dataset(json_data)

    print(ds.get_bioprofile())