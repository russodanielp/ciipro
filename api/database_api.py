from flask import Blueprint, request, jsonify, session
from api.databases import AVAILABLE_DATABASES, master, ACTIVITY_MAPPER, NAME_MAPPER

api = Blueprint('api', 'api', url_prefix='/api')

@api.route('/databases/<database>')
def get_database(database):

    if database not in AVAILABLE_DATABASES.keys():
        return "database not found"

    smiles_string = 'SMILES' if database != 'bioavailability' else 'Updated SMILES'

    results = master.find({database: {'$exists': True}}, {database: 1, '_id': 0})

    acute_oral_db = AVAILABLE_DATABASES[database].find({"_id": {"$in": [result[database] for result in results]}},
                                    {smiles_string: 1, ACTIVITY_MAPPER[database]: 1, NAME_MAPPER[database]: 1, '_id': 0})

    return jsonify(list(acute_oral_db))