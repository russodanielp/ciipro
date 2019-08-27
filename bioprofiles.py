""" Model that contains class for interacting with bioprofiles """


import json, os
import pandas as pd
import numpy as np
from pc_mongodb import bioassays_db

class Bioprofile:


    def __init__(self,
                 name,
                 cids,
                 aids,
                 outcomes,
                 stats,
                 meta):
        """ profile should have a name, a list of cids and a list of aids and and list of outcomes,
        order matters for these as cids[i], aids[i], outcomes[i] represents a compounds outcome in an assays,
        similarly, stats are the calculated stats for that assay with the training set
        """
        self.name = name
        self.cids = cids
        self.aids = aids
        self.outcomes = outcomes
        self.stats = stats
        self.meta = meta


    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def to_json(self, write_dir):
        json_data = {
            'name': self.name,
            'cids': self.cids,
            'aids': self.aids,
            'outcomes': self.outcomes,
            'stats': self.stats,
            'meta': self.meta
        }


        with open(os.path.join(write_dir, '{}.json'.format(self.name)), 'w') as outfile:
            json.dump(json_data, outfile)


    def to_frame(self):
        # the agg funtion should give preferences to activtes

        data = {
            'cids': self.cids,
            'aids': self.aids,
            'outcomes': self.outcomes
        }

        df = pd.DataFrame(data)

        profile = df.pivot_table(index='cids', columns='aids', values='outcomes', aggfunc=np.max).fillna(0)

        profile.index = list(map(int, profile.index))
        profile.columns = list(map(int, profile.columns))
        return profile

    def classification_overview(self):
        """ returns a dataframe of the actives and inactives counts for each assay in the bioprofile """

        df = self.to_frame().astype(float)

        class_overview = pd.DataFrame()
        class_overview['actives'] = (df == 1).sum()
        class_overview['inactives'] = (df == -1).sum()

        return class_overview

    def get_bioassay_info(self):
        unique_aids = [str(aid) for aid in set(self.aids)]
        return bioassays_db.query_list(unique_aids, 'AID', ['Source', 'Description'])


    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)
        return cls(json_data['name'],
                   json_data['cids'],
                   json_data['aids'],
                   json_data['outcomes'],
                   json_data['stats'],
                   json_data['meta'])

if __name__ == '__main__':
    import pandas as pd

    fake_query = pd.read_csv('resources/bioprofile.csv')

    bioprofile = Bioprofile.from_json('resources/my_profile.json')

    print(bioprofile.get_bioassay_info())