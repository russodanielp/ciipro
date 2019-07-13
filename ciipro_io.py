""" just read and writing files """

def parse_upload_file(filename):
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

