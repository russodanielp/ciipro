""" Model that contains class for interacting with fpprofiles """


import json, os
import pandas as pd


class FPprofile:


    def __init__(self,
                 name,
                 aids,
                 fps,
                 p_values,
                 meta):
        """ profile should have a name, a list of cids and a list of aids and and list of outcomes,
        order matters for these as cids[i], aids[i], outcomes[i] represents a compounds outcome in an assays,
        similarly, stats are the calculated stats for that assay with the training set
        """
        self.name = name
        self.aids = aids
        self.fps = fps
        self.p_values = p_values
        self.meta = meta


    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def to_json(self, write_dir):
        json_data = {
            'name': self.name,
            'aids': self.aids,
            'fps': self.fps,
            'p_values': self.p_values,
            'meta': self.meta
        }


        with open(os.path.join(write_dir, '{}.json'.format(self.name)), 'w') as outfile:
            json.dump(json_data, outfile)


    def to_frame(self):
        # the agg funtion should give preferences to activtes

        data = {
            'aids': self.aids,
            'fps': self.fps,
            'p_values': self.p_values
        }

        df = pd.DataFrame(data)

        profile = df.pivot_table(index='aids', columns='fps', values='p_values').fillna(0)

        profile.index = list(map(int, profile.index))
        profile.columns = list(map(int, profile.columns))
        return profile

    @classmethod
    def from_dict(cls, dictionary):

        aids = []
        fps = []
        p_values = []

        for aid, fp_dict in dictionary.items():
            for fp, p_value in fp_dict.items():
                aids.append(aids)
                fps.append(fp)
                p_values.append(p_value)


        return cls('name',
                   aids,
                   fps,
                   p_values,
                   None)

if __name__ == '__main__':
    pass