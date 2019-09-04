from scipy.stats import fisher_exact
from collections import defaultdict

def in_vitro_in_vivo_correlations(bioprofile, fps, threshold=1.01, binarize=False):
    """ uses fishers exact test to find the correlations between every
     fingerprint in fps to every bioassay in bioprofile_matrix """
    aid_fp_dict = defaultdict(dict)


    for aid, assay_data in bioprofile.iteritems():

        assay_data_wo_null = assay_data.dropna()

        actives = assay_data_wo_null[assay_data_wo_null == 1]
        inactives = assay_data_wo_null[assay_data_wo_null == -1]


        # only check aid if actives and inactives > 0
        if ((actives.shape[0] > 0)  and (inactives.shape[0] > 0)):

            for fp, fp_data in fps.iteritems():
                cmps_with_fp = fp_data[fp_data == 1]
                cmps_without_fp = fp_data[fp_data == 0]

                # find the distributions of active/inactive responses
                # and absence/presence of fp
                act_and_fp = actives.index.intersection(cmps_with_fp.index).shape[0]
                act_and_wo_fp = actives.index.intersection(cmps_without_fp.index).shape[0]

                inact_and_fp = inactives.index.intersection(cmps_with_fp.index).shape[0]
                inactive_and_wo_fp = inactives.index.intersection(cmps_without_fp.index).shape[0]


                assert (actives.shape[0] + inactives.shape[0]) == (act_and_fp + act_and_wo_fp + inact_and_fp + inactive_and_wo_fp)

                confusion_matrix = [
                                        [act_and_fp, act_and_wo_fp],
                                        [inact_and_fp, inactive_and_wo_fp]
                ]

                oddsratio, pvalue = fisher_exact(confusion_matrix)

                if pvalue < threshold:
                    if binarize:
                        aid_fp_dict[aid][fp] = 1
                    else:
                        aid_fp_dict[aid][fp] = pvalue

    return aid_fp_dict