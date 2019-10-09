""" Model that contains class for interacting with fpprofiles """


import json, os
import pandas as pd
from sklearn.metrics.pairwise import pairwise_distances
from scipy.spatial.distance import pdist, squareform
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import linkage


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

    def get_adjacency(self, metric='jaccard', min_distance=0.6, min_connections=1):
        """
        calculates an adjacency matrix from fingerprint profile

        :param metric: metric to use to calculate distance
        :param min_distance: minumum distance to make a connection between two nodes
        :return:
        """
        X = self.to_frame()

        distances = pdist(X, metric=metric)

        connectivity_matrix = pd.DataFrame(squareform(distances), index=X.index, columns=X.index)


        nodes = []
        for idx, aid in enumerate(X.index):
            nodes.append({"id": int(aid), "name": int(aid)})

        links = []

        num_connections = {}

        for aid_one in connectivity_matrix.index:
            for aid_two in connectivity_matrix.index:
                if (aid_one != aid_two) and (connectivity_matrix.loc[aid_one, aid_two] <= min_distance):
                    data = {"source": int(aid_one),
                            "target": int(aid_two),
                            "weight": float(connectivity_matrix.loc[aid_one, aid_two])}
                    links.append(data)

                    num_connections[int(aid_one)] = num_connections.get(int(aid_one), 0) + 1







        adj_matrix = AdjMatrix(nodes, links, self.name, None)
        adj_matrix_new = remove_singletons(adj_matrix)

        non_singletons = [node["id"] for node in adj_matrix_new.nodes]

        con_matrix_no_singletons = connectivity_matrix.loc[connectivity_matrix.index.isin(non_singletons),
                                                      connectivity_matrix.columns.isin(non_singletons)]

        # get a new connectivity matrix with the singletons removed

        distances = squareform(con_matrix_no_singletons.values)

        # add classes to the nodes
        for i, node in enumerate(adj_matrix_new.nodes):
            node["class"] = i

        Z = linkage(distances, method='single').tolist()
        adj_matrix_new.linkage = Z

        return adj_matrix_new


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

    def __init__(self, nodes, links, profile_used, linkage):

        self.nodes = nodes
        self.links = links
        self.profile_used = profile_used
        self.linkage = linkage


    def to_json(self, write_dir):
        json_data = {
            'nodes': self.nodes,
            'links': self.links,
            'profile_used': self.profile_used,
            'linkage': self.linkage
        }
        with open(os.path.join(write_dir, '{}_adj_matrix.json'.format(self.profile_used)), 'w') as outfile:
            json.dump(json_data, outfile, indent=4)

    @classmethod
    def from_json(cls, json_filename):
        with open(json_filename) as json_file:
            json_data = json.load(json_file)

        return cls(json_data['nodes'],
                   json_data['links'],
                   json_data['profile_used'],
                   json_data['linkage'])



def remove_singletons(adj_matrix):
    """ removes nodes that are singletons, ie., have no other links in the set """
    final_nodes = adj_matrix.nodes.copy()
    final_links = adj_matrix.links.copy()

    num_connections = {}
    print(len(final_nodes), len(adj_matrix.nodes))

    for link in adj_matrix.links:

        aid = link["source"]
        num_connections[int(aid)] = num_connections.get(int(aid), 0) + 1


    nodes_to_remove = []
    links_to_remove = []

    for i, node in enumerate(adj_matrix.nodes):
        if num_connections.get(node["id"], 0) <= 0:
            nodes_to_remove.append(i)

    for i, link in enumerate(adj_matrix.links):
        if num_connections.get(link["source"], 0) <= 0:
            links_to_remove.append(i)


    nodes_to_remove = sorted(nodes_to_remove, reverse=True)
    links_to_remove = sorted(links_to_remove, reverse=True)


    for node_to_remove in nodes_to_remove:
        del final_nodes[node_to_remove]
    for link_to_remove in links_to_remove:
        del final_links[link_to_remove]

    return AdjMatrix(final_nodes, final_links, adj_matrix.profile_used, adj_matrix.linkage)

if __name__ == '__main__':

    import os

    adj_json_file = os.path.join(os.getenv('CIIPRO_DATA'), 'Guest', 'fp_profiles', 'acute_oral_toxicity_profile_9_27_2019_clustering_adj_matrix.json')


    adj_matrix = AdjMatrix.from_json(adj_json_file)

    adj_matrix_new = removed_singletons(adj_matrix)

    adj_matrix_new.profile_used = "new_clustering"
    adj_matrix_new.to_json(os.path.join(os.getenv('CIIPRO_DATA'), 'Guest', 'fp_profiles'))