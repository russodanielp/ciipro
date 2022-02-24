from ciipro_config import CIIProConfig

def allowed_file(filename): #method that checks to see if upload file is allowed
    return '.' in filename and filename.rsplit('.', 1)[1] in CIIProConfig.ALLOWED_EXTENSIONS


def allowed_curation(filename): #method that checks to see if upload file is allowed
    return '.' in filename and filename.rsplit('.', 1)[1] in ['sdf', 'txt']
