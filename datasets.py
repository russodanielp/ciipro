""" Module for users datasets """
from typing import List

import pandas as pd
from pc_mongodb import compounds_db, synonyms_db, outcomes_db

import pandas as pd
import numpy as np

import json, os
from collections import ChainMap

class DataSet:

    def __init__(self, name: str,
                 compounds: List,
                 activities: List,
                 set_type: str,
                 identifier_type='CID'):
        """  to do  """

        self.name = name
        self.compounds = compounds
        self.activities = activities
        self.id_type = identifier_type
        self.set_type = set_type

    def __repr__(self):
        return "{}".format(self.name)

    def __str__(self):
        return self.__repr__()

    def get_cids(self):
        """ converts identifier from the native """

        if self.id_type == 'cid':
            return compounds_db.query_list(self.compounds, 'CID', ['CID'])
        elif self.id_type == 'cas':
            return synonyms_db.query_list(self.compounds, 'Synonym', ['Synonym', 'CID'])
        elif self.id_type == 'smiles':
            return compounds_db.query_list(self.compounds, 'SMILES Canonical', ['SMILES Canonical', 'CID'])
        elif self.id_type == 'iupac':
            return compounds_db.query_list(self.compounds, 'IUPAC Name Preferred', ['IUPAC Name Preferred', 'CID'])

    def get_assays(self):
        """ queries the outcomes databases to get assays """

        cids = [cmp['CID'] for cmp in self.get_cids()]
        assays = outcomes_db.query_list(cids, 'CID', ['AID', 'Outcome'])
        return assays

    def get_activities(self, use_cids=False):
        if not use_cids:
            return pd.Series(self.activities, index=self.compounds)
        else:
            # MongoDB does not return documents in the order querired, so need to re-orient

            query_list = self.get_cids()
            cids = []
            other_id = []

            # TODO:
            # gotta be a better way to do this.....
            for cmp_dict in query_list:

                # should be a dictionary of two keys
                # one will def by cid, but the other could be any
                for identifier, identifer_value in cmp_dict.items():

                    # we want to key by the native identifer, which is not the CID
                    if identifier != 'CID':
                        other_id.append(identifer_value)
                    else:
                        cids.append(identifer_value)

            mapping_dict = dict(zip(other_id, cids))

            # not every compound in the database iwll have a cid

            dict_to_series = {}

            for act, identifier in zip(self.activities, self.compounds):
                cid = mapping_dict.get(identifier, None)
                if cid:
                    dict_to_series[cid] = act

            # use the mapping dictionary to properly assign acts to cids
            return pd.Series(dict_to_series)

    def get_bioprofile(self, min_actives=0):

        assays = self.get_assays()

        # need to convert to numbers for pandas

        for assay_data in assays:
            if assay_data['Outcome'] == 'Active':
                assay_data['Outcome'] = 1
            elif assay_data['Outcome'] == 'Inactive':
                assay_data['Outcome'] = -1
            else:
                assay_data['Outcome'] = 0

            assay_data['CID'] = int(assay_data['CID'])
            assay_data['AID'] = int(assay_data['AID'])

        # the agg function should give preferences to activtes
        df = pd.DataFrame(assays).pivot_table(index='CID', columns='AID', values='Outcome', aggfunc=np.max)

        df = df.loc[:, ((df == 1).sum() >= min_actives)].replace(0, np.nan)

        df = df.unstack().reset_index(name='value').dropna()

        df = df.rename(index=str, columns={"CID": "cids", "AID": "aids", "value": "outcomes"})

        json_ob = df.to_dict('list')

        for col in ['cids', 'aids', 'outcomes']:
            json_ob[col] = list(map(int, json_ob[col]))

        return json_ob

    def to_json(self, profiles_dir: str):
        with open(os.path.join(profiles_dir, '{}.json'.format(self.name))) as json_file:
            json_data = json.load(json_file)
        return json_data

    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)

        name = json_data['overview']['name']
        identifier_type = json_data['overview']['identifier_type']
        set_type = json_data['overview']['set_type']
        identifiers = [compound['identifier'] for compound in json_data['compounds']]
        activities = [compound['activity'] for compound in json_data['compounds']]
        return DataSet(name, identifiers, activities, set_type, identifier_type)
        return cls(json_data['name'], json_data['cids'], json_data['aids'], json_data['outcomes'])



def make_dataset(dataset_json):
    """ takes the json of a dataset and makes a dataset object """
    name = dataset_json['overview']['name']
    identifier_type = dataset_json['overview']['identifier_type']
    set_type = dataset_json['overview']['set_type']
    identifiers = [compound['identifier'] for compound in dataset_json['compounds']]
    activities = [compound['activity'] for compound in dataset_json['compounds']]
    return DataSet(name, identifiers, activities, set_type, identifier_type)


if __name__ == '__main__':

    # this is just for testing

    import datasets_io

    json_data = datasets_io.load_json(r'D:\ciipro\Guest\datasets\ER_train_can.json')
    ds = make_dataset(json_data)
    print(ds.get_activities(use_cids=True))
    #print(ds.get_bioprofile())