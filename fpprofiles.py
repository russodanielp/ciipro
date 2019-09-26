""" Model that contains class for interacting with fpprofiles """


import json, os
import pandas as pd
from sklearn.metrics.pairwise import pairwise_distances
from sklearn.cluster import AgglomerativeClustering



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
            json.dump(json_data, outfile, indent=4)


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

    def get_adjacency(self, metric='jaccard', min_distance=0.5, n_clusters=5):
        """
        calculates an adjacency matrix from fingerprint profile

        :param metric: metric to use to calculate distance
        :param min_distance: minumum distance to make a connection between two nodes
        :return:
        """
        X = self.to_frame()

        connectivity_matrix = pd.DataFrame(pairwise_distances(X, metric=metric), index=X.index, columns=X.index)

        cluster = AgglomerativeClustering(n_clusters=n_clusters, affinity='precomputed', linkage='average')

        cluster.fit(connectivity_matrix)

        nodes = []
        for idx, aid in enumerate(X.index):
            nodes.append({"id": int(aid), "name": int(aid), "class": int(cluster.labels_[idx])})

        links = []

        for aid_one in connectivity_matrix.index:
            for aid_two in connectivity_matrix.index:
                if (aid_one != aid_two) and (connectivity_matrix.loc[aid_one, aid_two] <= min_distance):
                    data = {"source": int(aid_one),
                            "target": int(aid_two),
                            "weight": float(connectivity_matrix.loc[aid_one, aid_two])}
                    links.append(data)
        return AdjMatrix(nodes, links, self.name)


    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)

        return cls(json_data['name'],
                   json_data['aids'],
                   json_data['fps'],
                   json_data['p_values'],
                   json_data['meta']
                   )

    @classmethod
    def from_dict(cls, dictionary):

        aids = []
        fps = []
        p_values = []

        for aid, fp_dict in dictionary.items():
            for fp, p_value in fp_dict.items():
                aids.append(int(aid))
                fps.append(int(fp))
                p_values.append(float(p_value))


        return cls(None,
                   aids,
                   fps,
                   p_values,
                   None)



class AdjMatrix:

    def __init__(self, nodes, links, profile_used):

        self.nodes = nodes
        self.links = links
        self.profile_used = profile_used


    def to_json(self, write_dir):
        json_data = {
            'nodes': self.nodes,
            'links': self.links,
            'profile_used': self.profile_used,
        }
        with open(os.path.join(write_dir, '{}_adj_matrix.json'.format(self.profile_used)), 'w') as outfile:
            json.dump(json_data, outfile, indent=4)

    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)

        return cls(json_data['nodes'],
                   json_data['links'],
                   json_data['profile_used'])


if __name__ == '__main__':
    pass