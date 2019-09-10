""" just read and writing files """

import json, glob, os

def parse_upload_file(filename: str):
    identifiers = []
    activities = []
    f = open(filename, 'r')

    for line in f:
        line = line.strip()

        identifier = line.split('\t')[0].strip()
        activity = line.split('\t')[1].strip()

        identifiers.append(identifier)
        activities.append(activity)

    return identifiers, activities

def get_all_json_files(dir: str):
    return glob.glob(os.path.join(dir, '*.json'))

def load_json(dir):
    """ simply loads a json dataset """

    with open(dir) as json_file:
        json_data = json.load(json_file)
    return json_data


def get_profiles_names_for_user(profiles_dir: str):

    # TODO: find a better way to not get adj_matrix file
    all_jsons = [json_file for json_file in glob.glob(os.path.join(profiles_dir, '*.json'))
                 if 'adj_matrix' not in json_file]
    names = []

    for json_file in all_jsons:
        profile = load_json(json_file)
        names.append(profile['name'])
    return names