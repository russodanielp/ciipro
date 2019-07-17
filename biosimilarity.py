import numpy as np
import scipy.spatial.distance as scipydis

def biosimilarity_distances(X, X_, weight=0.1, normalize_conf=True):
    """ calculate the distance of every element of X in X_

        will return two matrices of biodis/conf of shape (X.shape[0], X_.shape[0]),
        ie., biodis[i, j] is the biodistance between X[i, :] and X_[j, :]

    """

    # TODO: find a cleaner way to do this

    X_new = np.concatenate([X, X_])

    positives = X_new.copy()
    positives[X_new == -1] = 0

    negatives = X_new.copy()
    negatives[X_new == 1] = 0


    weighted_negatives = negatives * weight

    tot_pos = positives.dot(positives.T)
    tot_neg = negatives.dot(weighted_negatives.T)
    diff_0 = positives.dot(negatives.T)
    diff = np.minimum(diff_0, diff_0.T)

    numer = tot_pos + tot_neg
    denom = tot_pos + tot_neg - diff

    biodis, conf = np.nan_to_num(1 - (numer / denom)), denom

    # if we want to "normalize" we device the confidence matrix by
    # the number of columns, which would be the highest possible confidence
    # i.e., two compounds share all actives in all assays

    if normalize_conf :
        max_conf = X_new.shape[1]
        conf_normed = conf / max_conf
        return biodis[:len(X), len(X):], conf_normed[:len(X), len(X):]

    return biodis[:len(X), len(X):], conf[:len(X), len(X):]


def get_k_bioneighbors(biosim, conf, k=1, biosim_cutoff=0.75, conf_cutoff=0.5):
    """
        Given a biodis, conf matrix of the shape n x m, where
        each cell is either a biosim calc or a confidence value,
        where rows are assumed to be "test compounds" and
        columns are assumed to be "training compounds", it will find
        the k nearest m-pints for each n

    """

    # lex sort returns n arrays of m length, where values represent
    # the sorted order for that particular sorting
    # first sort by confidence, then by biodistance
    # this sorts by second matrix first, the first matrix
    NNs = np.lexsort([biosim, conf])


    # since it sorts in ascending order, flipping left to right esentiall
    NNs = np.fliplr(NNs)


    # a point can't be its own nearest neighbor
    # so remove it and reverse order
    new = []
    for i, row in enumerate(NNs):

        # new row is a 1-D array of NN indices in descending order
        new_row = row.copy()

        # remove neighbors that dont meet confidence or bio sim
        # TODO: figure out a better way to do this
        for nn in new_row.copy():
            if (biosim[i, nn] < biosim_cutoff) or (conf[i, nn] < conf_cutoff):
                index = np.where(new_row == nn)
                new_row = np.delete(new_row, index)

        new.append(new_row[:k])
    return np.array(new)

def chem_distances(X, X_, metric='jaccard'):
    X_new = np.concatenate([X, X_])
    print(X_new.shape)
    chem_dist_cond = scipydis.pdist(X_new, metric)
    chem_dist = scipydis.squareform(chem_dist_cond)
    print(chem_dist.shape)
    return chem_dist[:len(X), len(X):]


def get_k_chem_neighbors(similarities, k=1):

    NNs = np.argsort(similarities)
    # since it sorts in ascending order, flipping left to right esentiall
    NNs = np.fliplr(NNs)

    new = []
    for i, row in enumerate(NNs):

        # new row is a 1-D array of NN indices in descending order
        new_row = row.copy()
        new.append(new_row[:k])
    return np.array(new)

    return NNs[:, k]



if __name__ == '__main__':

    # this is all for testing

    from bioprofiles import Bioprofile
    from datasets import DataSet

    training_profile = Bioprofile.from_json(r'D:\ciipro\Guest\profiles\a_er.json')

    training_matrix = training_profile.to_frame()

    training_data = DataSet.from_json(r'D:\ciipro\Guest\datasets\ER_train_can.json')

    test_data = DataSet.from_json(r'D:\ciipro\Guest\datasets\ER_test_can.json')

    # get a full test set profile
    print(training_data, test_data)
    test_profile_json = test_data.get_bioprofile()

    # I guess since a lot of these dont get used might be better to
    # create two classes one for training profiles and one for test
    test_profile = Bioprofile('test',
                                 test_profile_json['cids'],
                                 test_profile_json['aids'],
                                 test_profile_json['outcomes'],
                                 None,
                                 None)

    test_matrix = test_profile.to_frame()


    # only use the intersection of the test profile and the training profile
    shared_assays = training_matrix.columns.intersection(test_matrix.columns)

    test_matrix = test_matrix.loc[:, shared_assays]
    training_matrix = training_matrix.loc[:, shared_assays]

    test_matrix.replace(0, 1, inplace=True)
    training_matrix.replace(0, 1, inplace=True)

    biodis, conf = biosimilarity_distances(test_matrix.values, training_matrix.values)
    biosim = 1-biodis

    nns_arr = get_k_bioneighbors(biosim, conf, biosim_cutoff=0.5, conf_cutoff=0.5)



    test_fps = test_data.get_pubchem_fps()
    train_fps = training_data.get_pubchem_fps()

    chem_dis = chem_distances(test_fps, train_fps)
    chem_nns = get_k_chem_neighbors(1-chem_dis)

    for i, chem_nn in enumerate(chem_nns):
        print(test_fps.index[i], train_fps.index[chem_nn[0]])


