""" Model that contains class for interacting with bioprofiles """

from typing import List
import json, os
import pandas as pd
import numpy as np

class Bioprofile:


    def __init__(self, name:str, cids: List, aids: List, outcomes: List):
        self.name = name
        self.cids = cids
        self.aids = aids
        self.outcomes = outcomes


    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def to_json(self, write_dir: str):
        json_data = {
            'name': self.name,
            'cids': self.cids,
            'aids': self.aids,
            'outcomes': self.outcomes
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
        return df.pivot_table(index='cids', columns='aids', values='outcomes', aggfunc=np.max).fillna(0)

    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)
        return cls(json_data['name'], json_data['cids'], json_data['aids'], json_data['outcomes'])

if __name__ == '__main__':
    import pandas as pd

    fake_query = pd.read_csv('resources/bioprofile.csv')



    bioprofile = Bioprofile.from_json('resources/my_profile.json')

    print(bioprofile.to_frame())