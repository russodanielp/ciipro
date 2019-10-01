from flask import Blueprint, request, jsonify, session
from .databases import AVAILABLE_DATABASES, master, bit_counts, ACTIVITY_MAPPER, NAME_MAPPER
from rdkit import Chem
from rdkit.Chem import AllChem
from rdkit import rdBase

#print(rdBase.rdkitVersion)
import sys

print(sys.executable)

api = Blueprint('api', 'api', url_prefix='/api')

@api.route('/databases/<database>')
def get_database(database):

    if (database not in AVAILABLE_DATABASES.keys()) and (database != 'master'):
        return "database not found"


    if database != 'master':

        smiles_string = 'SMILES' if database != 'bioavailability' else 'Updated SMILES'

        results = master.find({database: {'$exists': True}}, {database: 1, '_id': 0})

        acute_oral_db = AVAILABLE_DATABASES[database].find({"_id": {"$in": [result[database] for result in results]},
                                                            ACTIVITY_MAPPER[database]: {"$exists": True}
                                                            },
                                        {smiles_string: 1, ACTIVITY_MAPPER[database]: 1, NAME_MAPPER[database]: 1, '_id': 0})
        acute_oral_db = list(acute_oral_db)
        print(acute_oral_db)
        return jsonify(results=acute_oral_db)

    else:
        mols_to_send = []

        for molecule in master.find({}):
            record_to_send = {}
            record_to_send['activities'] = {}

            # smiles = Chem.MolToSmiles(Chem.Mol(molecule['mol']))
            # record_to_send['smiles'] = smiles
            record_to_send['zhu_id'] = molecule['zhu_id']
            for db in AVAILABLE_DATABASES.keys():
                if molecule.get(db, False):
                    db_results = AVAILABLE_DATABASES[db].find_one({"_id": molecule[db]}, {
                        ACTIVITY_MAPPER[db]: 1,
                        NAME_MAPPER[db]: 1,
                        '_id': 0})
                    record_to_send['activities'][db] = db_results

            mols_to_send.append(record_to_send)
        return jsonify(results=mols_to_send)

@api.route('/get_t_similar/<smiles>/<threshold>')
def get_t_similar(smiles, threshold):

    smiles = str(smiles)
    threshold = float(threshold)
    query_mol = Chem.MolFromSmiles(smiles)

    query_fp = list(AllChem.GetMorganFingerprintAsBitVect(query_mol, 3, nBits=2048).GetOnBits())

    qn = len(query_fp)

    qmin = int(qn * threshold)
    qmax = int(qn / threshold)
    reqbits = [count['_id'] for count in bit_counts.find({'_id': {'$in': query_fp}}).sort('count', 1).limit(qn - qmin + 1)]

    similar_mols = []

    for molecule in master.find({'fp.bits': {'$in': reqbits}, 'fp.len': {'$gte': qmin, '$lte': qmax}}):
        intersection = len(set(query_fp) & set(molecule['fp']['bits']))
        pn = molecule['fp']['len']
        tanimoto = float(intersection) / (pn + qn - intersection)
        if tanimoto > threshold:

            record_to_send = {}
            record_to_send['activities'] = {}

            smiles = Chem.MolToSmiles(Chem.Mol(molecule['mol']))
            record_to_send['smiles'] = smiles
            record_to_send['zhu_id'] = molecule['zhu_id']
            record_to_send['similarity'] = tanimoto
            for db in AVAILABLE_DATABASES.keys():
                if molecule.get(db, False):
                    db_results = AVAILABLE_DATABASES[db].find_one({"_id": molecule[db]}, {
                                                                                     ACTIVITY_MAPPER[db]: 1,
                                                                                     NAME_MAPPER[db]: 1,
                                                                                     '_id': 0})
                    record_to_send['activities'][db] = db_results

            similar_mols.append(record_to_send)
    similar_mols = sorted(similar_mols, key=lambda mol: mol['similarity'], reverse=True)
    return jsonify(results=similar_mols)

