#!/usr/bin/python

import os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

import argparse
import numpy as np

from src.utils import io,ui

dataset_dir = BASE_DIR + '/datasets/npz/'

def raw_input_float(prompt):
    while True:
        try:
            return float(raw_input(prompt))
        except ValueError:
            print ui.fail_str('[FAIL]') + ' That is not a valid float.'

# Assumes that the atoms in each molecule are in the same order.
def read_concat_xyz(f):
	n_atoms = None

	R,z = [],[]
	for i,line in enumerate(f):
		line = line.strip()
		if not n_atoms:
			n_atoms = int(line)
			print '| Number atoms per geometry:      {:>7d}'.format(n_atoms)

		file_i, line_i = divmod(i, n_atoms+2)

		cols = line.split()
		if line_i >= 2:
			if file_i == 0: # first molecule
				z.append(io._z_str_to_z_dict[cols[0]])
			R.append(map(float,cols[1:4]))

		if file_i % 1000 == 0:
			sys.stdout.write("\r| Number geometries found so far: {:>7d}".format(file_i))
			sys.stdout.flush()
	sys.stdout.write("\r| Number geometries found so far: {:>7d}\n".format(file_i))
	sys.stdout.flush()

	# Only keep complete entries.
	R = R[:int(n_atoms * np.floor(len(R) / float(n_atoms)))]

	R = np.array(R).reshape(-1,n_atoms,3)
	z = np.array(z)

	f.close()
	return (R,z)

def read_out_file(f,col):

	T = []
	for i,line in enumerate(f):
		line = line.strip()
		if line[0] != '#': # Ignore comments.
			T.append(float(line.split()[col]))
		if i % 1000 == 0:
			sys.stdout.write("\r| Number lines processed so far:  {:>7d}".format(len(T)))
			sys.stdout.flush()
	sys.stdout.write("\r| Number lines processed so far:  {:>7d}\n".format(len(T)))
	sys.stdout.flush()

	return np.array(T)


parser = argparse.ArgumentParser(description='Creates a dataset from extended [TODO] format.')
parser.add_argument('geometries', metavar = '<geometries>',\
							   type    = argparse.FileType('r'),\
							   help	   = 'path to XYZ geometry file')
parser.add_argument('forces', metavar = '<forces>',\
							   type    = argparse.FileType('r'),\
							   help	   = 'path to XYZ force file')
parser.add_argument('energies', metavar = '<energies>',\
							   type    = argparse.FileType('r'),\
							   help	   = 'path to CSV force file')
parser.add_argument('energy_col', 	 metavar = '<energy_col>',\
							  	 type    = lambda x: ui.is_strict_pos_int(x),\
							  	 help    = '[TODO]',\
							  	 nargs   = '?', default = 0)
args = parser.parse_args()
geometries = args.geometries
forces = args.forces
energies = args.energies
energy_col = args.energy_col


print 'Reading geometries...'
R,z = read_concat_xyz(geometries)

print 'Reading forces...'
TG,_ = read_concat_xyz(forces)

print 'Reading energies from column %d...' % energy_col
T = read_out_file(energies,energy_col)

# Prune all arrays to same length.
n_mols = min(min(R.shape[0], TG.shape[0]), T.shape[0])
if n_mols != R.shape[0] or n_mols != TG.shape[0] or n_mols != T.shape[0]:
	print ui.warn_str('[WARN]') + ' Incomplete output detected: Final dataset was pruned to %d points.' % n_mols
R = R[:n_mols,:,:]
TG = TG[:n_mols,:,:]
T = T[:n_mols]

print ui.info_str('[INFO]') + ' Geometries, forces and energies must have consistent units.'
R_conv_fact = raw_input_float('Unit conversion factor for geometries: ')
R = R * R_conv_fact
TG_conv_fact = raw_input_float('Unit conversion factor for forces: ')
TG = TG * TG_conv_fact
T_conv_fact = raw_input_float('Unit conversion factor for energies: ')
T = T * T_conv_fact

name = os.path.splitext(os.path.basename(geometries.name))[0]

# Base variables contained in every model file.
base_vars = {'R':				R,\
			 'z':				z,\
			 'T':				T[:,None],\
			 'TG':				TG,\
			 'name':			name,\
			 'theory_level':	'unknown'}

if not os.path.exists(dataset_dir):
	print ui.info_str(' [INFO]') + ' Created directory \'%s\'.' % 'datasets/npz/'
	os.makedirs(dataset_dir)
dataset_path = dataset_dir + name + '.npz'
print 'Writing dataset to \'datasets/npz/%s.npz\'...' % name
np.savez_compressed(dataset_path, **base_vars)
print ui.pass_str('DONE')