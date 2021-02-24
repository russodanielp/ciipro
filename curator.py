import checker as chkr
import standardizer as stdr
from rdkit import Chem
from typing import List
from itertools import groupby

class Curator:


    def __init__(self, original_mols: List[Chem.Mol], exclude_level=7):
        """

        :param original_mols: List of RDKit mols
        """

        self.o_mols = original_mols
        self.el = 7

    def check_cmps(self):
        self.flags = [chkr.check_molblock(Chem.MolToMolBlock(m)) if m else ((7, 'Structure Error'),) for m in self.o_mols]

    def standardize(self):
        if not hasattr(self, 'flags'):
            self.check_cmps()

        standardized_mols = []
        for i, mol_flags in enumerate(self.flags):
            if mol_flags and any(flag[0] >= self.el for flag in mol_flags):
                standardized_mols.append(None)
            else:
                standardized_mols.append(stdr.standardize_mol(self.o_mols[i]))
        self.s_mols = standardized_mols

    def get_parents(self):
        if not hasattr(self, 's_mols'):
            self.standardize()

        children_mol = []
        for i, mol in enumerate(self.s_mols):
            if not mol:
                children_mol.append(None)
            else:
                child, _ = stdr.get_parent_mol(mol)
                children_mol.append(child)
        self.c_mols = children_mol

    def identify_duplicates(self):
        if not hasattr(self, 'c_mols'):
            self.get_parents()

        ids = []
        unique_inchi = []
        duplicated_bools = []
        inchi = [Chem.MolToInchi(m) if m else m for m in self.c_mols]

        grp_num = 0
        for key, group in groupby(sorted(inchi)):

            duplicated = len(list(group)) > 1

            for inchi in group:
                unique_inchi.append(inchi)
                ids.append('Mol_{}'.format(grp_num))
                duplicated_bools.appened(True if duplicated else False)
            grp_num = grp_num + 1

        self.ids = ids
        self.u_mols = [Chem.MolFromInchi(inchi) if inchi else inchi for inchi in unique_inchi]
        self.duplicated = duplicated_bools


def to_2d(mols):
    """
    converts every mol in mols to 2D by converting from a mol
    to SMILES and back again.
    """
    return [Chem.MolFromSmiles(Chem.MolToSmiles(m)) if m else m for m in mols]


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Chemical Curator.')
    parser.add_argument('--file_in', help='SDFile location')
    parser.add_argument('--out', help='SDFile location')

    args = parser.parse_args()

    mols = [m if m else None for m in Chem.SDMolSupplier(args.file_in)]

    print("Loaded {} molecules".format(len(mols)))

    mols = to_2d(mols)

    curator = Curator(mols)
    curator.identify_duplicates()

    print("There are {} duplicates".format(sum(curator.duplicated)))
    print("There are {} compounds with errors".format(sum([True if f else False for f in curator.flags])))

    w = Chem.SDWriter(args.out)

    for mol, dup, _id, flags in zip(curator.u_mols, curator.duplicated, curator.ids, curator.flags):
        mol.SetProp('Duplicated', '{}'.format(dup))
        mol.SetProp('ID', '{}'.format(_id))
        f_string = ''
        for f in flags:
            f_string = f_string + str(f[0]) + ': {}'.format(f[1]) + ';'
        mol.SetProp('Flags', f_string)
        w.write(mol)
    w.close()

