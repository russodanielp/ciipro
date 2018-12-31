import os
import pandas as pd

from keras import backend as K
from keras import models
from keras.losses import binary_crossentropy

from rdkit.Chem import MolFromSmiles, MACCSkeys, AllChem, rdchem

from sklearn.externals import joblib


def get_model_file_list(directory):
    ML_class_models = [model for model in os.listdir(directory) if (model[-4:] == '.pkl' and model[:3] != 'DNN' and
                                                                    model[:model.index('_')][-1] != 'r')]
    ML_regress_models = [model for model in os.listdir(directory) if (model[-4:] == '.pkl' and
                                                                      model[:model.index('_')][-1] == 'r')]
    DL_class_models = [model for model in os.listdir(directory) if (model[-4:] == '.pkl' and model[:3] == 'DNN')]
    ER_multitask_models = [model for model in os.listdir(directory) if 'ER_assays' in model]

    return ML_class_models, ML_regress_models, DL_class_models, ER_multitask_models


def make_display_list(model_file_list, algs):
    model_list = []
    for model in model_file_list:
        breaks = [index for index, character in enumerate(model) if character == '_']
        if model[:3] == 'DNN':
            avail_alg = algs[model[:breaks[1]]]
        else:
            avail_alg = algs[model[:breaks[0]]]
        if avail_alg not in model_list:
            model_list.append(avail_alg)

    return model_list


def generate_molecules(df):
    mols = []
    i = 0
    while i < len(df['SMILES']):
        for smiles in df['SMILES']:
            mol = MolFromSmiles(smiles)
            if mol is not None:
                mol.SetProp('CID', str(df.index[i]))
                mols.append(mol)
            i += 1

    return mols


def calc_fcfp6(molecules, name_col='CID'):
    """
    Takes in a list of rdkit molecules and returns FCFP6 fingerprints for a list of rdkit molecules

    :param name_col: Name of the field to index the resulting DataFrame.  Needs to be a valid property of all molecules
    :param molecules: List of rdkit molecules with no None values

    :return: pandas DataFrame of dimensions m x n, where m = # of descriptors and n = # of molecules
    """

    # Checks for appropriate input
    assert isinstance(molecules, list), 'The molecules entered are not in the form of a list.'
    assert all((isinstance(mol, rdchem.Mol) for mol in molecules)), 'The molecules entered are not rdkit Mol objects.'
    assert None not in molecules, 'The list of molecules entered contains None values.'
    assert isinstance(name_col, str), 'The input parameter name_col (%s) must be a string.' % name_col

    data = []

    for mol in molecules:
        fcfp6 = [int(x) for x in AllChem.GetMorganFingerprintAsBitVect(mol, 3, 1024, useFeatures=True)]
        data.append(fcfp6)

    return pd.DataFrame(data, index=[mol.GetProp(name_col) if mol.HasProp(name_col) else '' for mol in molecules])


def calc_maccs(molecules, name_col='CID'):
    """
    Takes in a list of rdkit molecules and returns MACCS fingerprints for a list of rdkit molecules

    :param name_col: Name of the field to index the resulting DataFrame.  Needs to be a valid property of all molecules
    :param molecules: List of rdkit molecules with no None values

    :return: pandas DataFrame of dimensions m x n, where m = # of descriptors and n = # of molecules
    """

    # Checks for appropriate input
    assert isinstance(molecules, list), 'The molecules entered are not in the form of a list.'
    assert all((isinstance(mol, rdchem.Mol) for mol in molecules)), 'The molecules entered are not rdkit Mol objects.'
    assert None not in molecules, 'The list of molecules entered contains None values.'
    assert isinstance(name_col, str), 'The input parameter name_col (%s) must be a string.' % name_col

    data = []

    for mol in molecules:
        maccs = [int(x) for x in MACCSkeys.GenMACCSKeys(mol)]
        data.append(maccs)

    return pd.DataFrame(data, index=[mol.GetProp(name_col) if mol.HasProp(name_col) else '' for mol in molecules])


descriptor_fxs = {
        'FCFP6': lambda mols: calc_fcfp6(mols, name_col='CID'),
        'MACCS': lambda mols: calc_maccs(mols, name_col='CID')
    }


def make_qsar_dataset(df, descriptors):
    """
    Takes in a Pandas DataFrame containing compound CID and SMILES information and returns a new DataFrame containing
    the calculated descriptors with CID as the index.
    :param df: Pandas DataFrame containing compound CID and SMILES information as columns
    :param descriptors: Desired descriptors to be calculated for the molecules, entered as a string
    :return: DataFrame of dimensions m x n, where m = # of descriptors and n = # of molecules
    """
    return descriptor_fxs[descriptors](generate_molecules(df))


def unpickle_ml_class_model(qsar_model_directory, algs, chosen_alg, descriptor):
    """
    Takes in information about a pickled machine learning QSAR model's location and the algorithm and descriptor used to
     build it and returns an unpickled model.
    :param qsar_model_directory: File path containing the QSAR model, entered as as string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :param descriptor: Descriptors to be used for predictions, entered as a string
    :return: Unpickled model
    """
    return joblib.load(os.path.join(qsar_model_directory,
                                    '{}_trainingset_171127_{}_LD50_mgkg_2000_pipeline.pkl'.format(
                                         list(algs.keys())[list(algs.values()).index(chosen_alg)],
                                         descriptor)))


def unpickle_ml_regress_model(qsar_model_directory, algs, chosen_alg, descriptor):
    """
    Takes in information about a pickled machine learning QSAR model's location and the algorithm and descriptor used to
     build it and returns an unpickled model.
    :param qsar_model_directory: File path containing the QSAR model, entered as as string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :param descriptor: Descriptors to be used for predictions, entered as a string
    :return: Unpickled model
    """
    return joblib.load(os.path.join(qsar_model_directory,
                                    '{}_trainingset_171127_{}_LD50_mgkg_pipeline.pkl'.format(
                                         list(algs.keys())[list(algs.values()).index(chosen_alg)],
                                         descriptor)))


def make_ml_class_predictions(descriptors, unpickled_test_set, qsar_model_directory, algs, chosen_alg):
    """
    Takes in information about the QSAR predictions a user wants to make, unpickles the appropriate model, and returns
    predictions
    :param descriptors: Descriptors to be used for predictions, entered as strings in a list
    :param unpickled_test_set: User test set as a Pandas DataFrame with CID and SMILES as separate columns
    :param qsar_model_directory: File path containing the QSAR model, entered as a string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :return: List containing predictions from each descriptor and list of compound CIDs
    """
    predictions = []
    for descriptor in descriptors:
        X = make_qsar_dataset(unpickled_test_set, descriptor)
        model = unpickle_ml_class_model(qsar_model_directory, algs, chosen_alg, descriptor)
        predictions.append(model.predict(X))
        if descriptors.index(descriptor) == len(descriptors) - 1:
            cids = X.index

    return predictions, cids


def make_ml_regress_predictions(descriptors, unpickled_test_set, qsar_model_directory, algs, chosen_alg):
    """
    Takes in information about the QSAR predictions a user wants to make, unpickles the appropriate model, and returns
    predictions
    :param descriptors: Descriptors to be used for predictions, entered as strings in a list
    :param unpickled_test_set: User test set as a Pandas DataFrame with CID and SMILES as separate columns
    :param qsar_model_directory: File path containing the QSAR model, entered as a string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :return: List containing predictions from each descriptor and list of compound CIDs
    """
    predictions = []
    for descriptor in descriptors:
        X = make_qsar_dataset(unpickled_test_set, descriptor)
        model = unpickle_ml_regress_model(qsar_model_directory, algs, chosen_alg, descriptor)
        predictions.append(model.predict(X))
        if descriptors.index(descriptor) == len(descriptors) - 1:
            cids = X.index

    return predictions, cids


def f1_score_k(y_true, y_pred):

    # Count positive samples.
    c1 = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    c2 = K.sum(K.round(K.clip(y_pred, 0, 1)))
    c3 = K.sum(K.round(K.clip(y_true, 0, 1)))

    # If there are no true samples, fix the F1 score at 0.
    if c3 == 0:
        return 0

    # How many selected items are relevant?
    precision = c1 / c2

    # How many relevant items are selected?
    recall = c1 / c3

    # Calculate f1_score
    f1_score = 2 * (precision * recall) / (precision + recall)
    return f1_score


def load_dl_model(qsar_model_directory, algs, chosen_alg, descriptor):
    """
    Takes in information about a deep learning QSAR model's location and the algorithm and descriptor used to
     build it and returns an loaded model.
    :param qsar_model_directory: File path containing the QSAR model, entered as a string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :param descriptor: Descriptors to be used for predictions, entered as strings in a list
    :return: Loaded model
    """
    pipe = joblib.load(os.path.join(qsar_model_directory, '{}_trainingset_171127_{}_LD50_mgkg_2000_pipeline.pkl'.format(
                                         list(algs.keys())[list(algs.values()).index(chosen_alg)],
                                         descriptor)))
    model = models.load_model(os.path.join(qsar_model_directory,
                                           '{}_trainingset_171127_{}_LD50_mgkg_2000_model.h5'.format(
                                               list(algs.keys())[list(algs.values()).index(chosen_alg)], descriptor)),
                              custom_objects={'f1_score_k': f1_score_k})
    pipe.steps.append(('clf', model))
    return pipe


def make_dl_predictions(descriptors, unpickled_test_set, qsar_model_directory, algs, chosen_alg):
    """
    Takes in information about the QSAR predictions a user wants to make, loads the appropriate model, and returns
    predictions
    :param descriptors: Descriptors to be used for predictions, entered as strings in a list
    :param unpickled_test_set: User test set as a Pandas DataFrame with CID and SMILES as separate columns
    :param qsar_model_directory: File path containing the QSAR model, entered as a string
    :param algs: Dictionary of with abbreviated alg names as they are in file names and full names as they are in the
    list a user chooses from
    :param chosen_alg: The full name of the alg chosen by the user to use for predictions
    :return: List containing predictions from each descriptor and list of compound CIDs
    """
    all_preds = []
    for descriptor in descriptors:
        X = make_qsar_dataset(unpickled_test_set, descriptor)
        model = load_dl_model(qsar_model_directory, algs, chosen_alg, descriptor)
        predictions = model.predict(X)
        if descriptors.index(descriptor) == len(descriptors) - 1:
            cids = X.index
        actives = predictions[:, 0] >= 0.5
        inactives = predictions[:, 0] < 0.5
        preds_class = predictions[:, 0].copy()
        preds_class[actives] = 1
        preds_class[inactives] = 0
        all_preds.append(preds_class)

    return all_preds, cids


def masked_loss_function(y_true, y_pred):
    mask = K.cast(K.not_equal(y_true, -1.00), K.floatx())
    return binary_crossentropy(y_true * mask, y_pred * mask)


def masked_accuracy(y_true, y_pred):
    return K.sum(K.cast(K.not_equal(y_true, -1.00), K.floatx())) / K.cast(K.equal(y_true, K.round(y_pred)),
                                                                               K.floatx())


def make_multitask_dl_predictions(descriptors, unpickled_test_set, qsar_model_directory):
    ER_ASSAYS = ['NVS_NR_bER', 'NVS_NR_hER', 'NVS_NR_mERa', 'OT_ER_ERaERa_0480', 'OT_ER_ERaERa_1440',
                 'OT_ER_ERaERb_0480', 'OT_ER_ERaERb_1440', 'OT_ER_ERbERb_0480', 'OT_ER_ERbERb_1440',
                 'OT_ERa_EREGFP_0120', 'OT_ERa_EREGFP_0480', 'ATG_ERa_TRANS_up', 'ATG_ERE_CIS_up',
                 'TOX21_ERa_BLA_Agonist_ratio', 'TOX21_ERa_LUC_BG1_Agonist', 'ACEA_T47D_80hr_Positive',
                 'TOX21_ERa_BLA_Antagonist_ratio', 'TOX21_ERa_LUC_BG1_Antagonist']
    all_preds = []

    for descriptor in descriptors:
        X = make_qsar_dataset(unpickled_test_set, descriptor)
        model = models.load_model(os.path.join(qsar_model_directory,
                                               'DNN_None_er_mdl_training_set_{}_ER_assays_class_model.h5'.format(
                                                   descriptor)), custom_objects={
            'masked_loss_function': masked_loss_function, 'masked_accuracy': masked_accuracy})
        raw_predictions = model.predict(X)
        all_preds.append(raw_predictions)

    all_consensus_preds = [(all_preds[0][i] + all_preds[1][i]) / 2 for i in range(len(ER_ASSAYS))]
    final_preds = []

    for assay, y_pred in zip(ER_ASSAYS, all_consensus_preds):
        y_class = y_pred.copy()
        y_class[y_pred >= 0.5] = 1
        y_class[y_pred < 0.5] = 0
        final_preds.append(y_class)

    return final_preds, X.index
