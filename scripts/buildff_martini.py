#!/usr/bin/env python3
import math
import argparse
import sys

# André Lanrezac

# https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/60f3ea062b910135237380eb/original/martini-3-coarse-grained-force-field-small-molecules.pdf
# http://cgmartini.nl/index.php/force-field-parameters/particle-definitions

residueName3To1 = {
        "ALA" : "A",
        "ARG" : "R",
        "ASN" : "N",
        "ASP" : "D",
        #"ASX" : "B",
        "CYS" : "C",
        "GLU" : "E",
        "GLN" : "Q",
        #"GLX" : "Z",
        "GLY" : "G",
        "HIS" : "H",
        #"HSD" : "H",
        #"HSE" : "H",
        #"HID" : "H",
        #"HSP" : "X",
        "ILE" : "I",
        "LEU" : "L",
        "LYS" : "K",
        "MET" : "M",
        "PHE" : "F",
        "PRO" : "P",
        "SER" : "S",
        "THR" : "T",
        "TRP" : "W",
        "TYR" : "Y",
        "VAL" : "V"
    }

# Hexadecane/Water partition kJ/mol
HD_WN = {
    "P2"  : -14.7,
    "SP2" : -16.0,
    "P1"  : -12.7,
    "SP2a": -13.9,
    "SN2d": -7.9,
    "SQp" : -58.0,
    "SP4" : -20.5,
    "SQn" : -58.7,
    "TC4" : 4.3,
    "Qn"  : -46.4,
    "P4"  : -19.4,
    "TC3" : 8.2,
    "TN3d": -11.2,
    "TN3a": -11.2,
    "SC1" : 16.2,
    "SC3" : 10.7,
    "C4"  : 8.9,
    "TP1" : -15.7,
    "SP1" : -14.0,
    "SC2" : 14.5
}

# Octanol/Water partition kJ/mol
OCOS_WN = {
    "P2"  : -2.6,
    "SP2" : -6.1,
    "P1"  : -1.1,
    "SP2a": -4.1,
    "SN2d": -0.3,
    "SQp" : -21.8,
    "SP4" : -9.2,
    "SQn" : -21.8,
    "TC4" : 6.2,
    "Qn"  : -14.7,
    "P4"  : -6.4,
    "TC3" : 8.0,
    "TN3d": -3.4,
    "TN3a": -3.4,
    "SC1" : 14.0,
    "SC3" : 10.3,
    "C4"  : 12.8,
    "TP1" : -5.9,
    "SP1" : -4.2,
    "SC2" : 13.0
}

choosed_partition = {}

bb_default = "P2"

# Specific BB beads
bb_specific = {
    "GLY": "SP2",
    "ALA": "P1",
    "PRO": "SP2a",
    "HYP": "P1"
}

sidechains = {
    "TRP": ["TC4", "TN3d", "TC4", "TC4", "TC4"],
    "TYR": ["TC3", "TC4", "TC4", "TP1"],
    "PHE": ["TC3", "TC4", "TC4"], 
    "HIS": ["TC3", "TN3d", "TN3a"],  
    "HIH": ["TC3", "TN3d", "TQp"], 
    "ARG": ["SN2d", "SQp"],
    "LYS": ["SC3", "SQp"],
    "CYS": ["TC4"],           
    "ASP": ["SQn"],            
    "GLU": ["Qn"],          
    "ILE": ["SC1"],           
    "LEU": ["SC1"],        
    "MET": ["C4"],            
    "ASN": ["SP4"],       
    "PRO": ["SC3"],         
    "HYP": ["P1"],          
    "GLN": ["P4"],            
    "SER": ["TP1"],         
    "THR": ["SP1"],           
    "VAL": ["SC2"],
    "ALA": [],
    "GLY": []
}

charges = {"Qp":1, "Qn":-1, "SQp":1, "SQn":-1, "TQp":1, "TQn":-1 }

# Bead size in Å, Regular Small and Tiny
b_sizes = {"R": 4.7, "S": 4.1, "T": 3.4}

# Bead mass in Da
b_masses = {"R": 72, "S": 54, "T": 36}

def get_bead_size_from_type(bead_type):
    if   (bead_type[0] == "S"): return b_sizes["S"]
    elif (bead_type[0] == "T"): return b_sizes["T"]
    else:                      return b_sizes["R"]

def get_bead_mass_from_type(bead_type):
    if   (bead_type[0] == "S"): return b_masses["S"]
    elif (bead_type[0] == "T"): return b_masses["T"]
    else:                      return b_masses["R"]
    
def get_bead_surface(size):
    return 4 * 3.1415926535898 * math.pow(size/2.0, 2)

def get_transfert_energy(bead_type):
    return -choosed_partition[bead_type] / get_bead_surface(get_bead_size_from_type(bead_type))

def read_nametotransfer_file(file_path):
    name_to_transfer = {}
    with open(file_path) as f:
        for line in f:
            (name, transfer) = line.split()
            name_to_transfer[name] = float(transfer)
    return name_to_transfer

def prep():

    # Write Reduce rule
    write_grp = open("../output/martini/reducerules/martini.grp", "w")
    for res3, res1 in residueName3To1.items():

        # Set BioSpring particle name for bb
        bb_name = res1 + "BB"
        write_grp.write("{} {} {}\n".format(bb_name, res3, "BB"))

        for i in range(len(sidechains[res3])):
            sc_code = "SC" + str(i+1)
            sc_name = res1 + sc_code
            write_grp.write("{} {} {}\n".format(sc_name, res3, sc_code))
    write_grp.close()    

    # Write Forcefield
    write_ff = open(output_filename, "w")
    ff_header = "#type	charge(e)	radius(A)	epsilon(kJ.mol-1)	mass(Da)	transferIMP(kJ.mol-1.A-2"
    write_ff.write(ff_header + "\n")
    for res3, res1 in residueName3To1.items():

        # Set BioSpring particle name for bb
        bb_name = res1 + "BB"

        # Get bb bead type
        bb_bead_type = bb_specific.get(res3, bb_default)
        
        charge = 0.0
        radius = get_bead_size_from_type(bb_bead_type)/2.0
        epsilon = 0.0
        mass = get_bead_mass_from_type(bb_bead_type)
        transfer_imp = name_to_transfer[bb_name] if name_to_transfer else get_transfert_energy(bb_bead_type)
        write_ff.write("{}\t{:.2f}\t{}\t{:.3f}\t{:.4f}\t{:.4f}\n".format(bb_name, charge, radius, epsilon, mass, transfer_imp))
        
        for i, sc_bead_type in enumerate(sidechains[res3]):
            sc_code = "SC" + str(i+1)
            sc_name = res1 + sc_code

            # The next obscure line get the charge value if it's a charged bead (with a Q letter), else null charge.
            charge = charges[list(filter(sc_bead_type.endswith, charges.keys()))[0]] if (sc_bead_type.endswith(tuple(charges.keys()))) else 0.0
            radius = get_bead_size_from_type(sc_bead_type)/2.0
            epsilon = 0.0
            mass = get_bead_mass_from_type(sc_bead_type)
            transfer_imp = name_to_transfer[sc_name] if name_to_transfer else get_transfert_energy(sc_bead_type)
            write_ff.write("{}\t{:.2f}\t{}\t{:.3f}\t{:.4f}\t{:.4f}\n".format(sc_name, charge, radius, epsilon, mass, transfer_imp))
    write_ff.close()

    # Write martini_name_to_type
    # write_martini_name_to_type = open("../data/forcefield/martini_nametotype.txt", "w")
    # for res3, res1 in residueName3To1.items():
    #     bb_name = res1 + "BB"
    #     bb_bead_type = bb_specific.get(res3, bb_default)
    #     write_martini_name_to_type.write("{}\t{}\n".format(bb_name,bb_bead_type))
    #     for i, sc_bead_type in enumerate(sidechains[res3]):
    #         sc_code = "SC" + str(i+1)
    #         sc_name = res1 + sc_code
    #         write_martini_name_to_type.write("{}\t{}\n".format(sc_name,sc_bead_type))
    # write_martini_name_to_type.close()

parser = argparse.ArgumentParser(description="Prepare Martini version 3.0.b.3.2 forcefield (.ff file) and reduce rule (.grp file) for pdb2spn.")

group = parser.add_mutually_exclusive_group()
group.add_argument('-ow','--oil-water', type=str, choices=['hexadecane', 'octanol'], help="Martini3 Oil/Water partition forcefield.")
group.add_argument('-c','--config_file', type=str, help="nametotransfert configuration file input.")
parser.add_argument('-o', type=str, help="Output forcefield file (mandatory if config file set).")

if __name__ == '__main__':
    args = parser.parse_args(sys.argv[1:])

    if (len(sys.argv[1:]) == 0):
        parser.print_help()
        parser.exit()

    
    
    name_to_transfer = {}
    if (args.config_file):
        if (args.o is None):
            parser.error("--config_file requires -o output_filename")
        else:
            output_filename = args.o

        name_to_transfer = read_nametotransfer_file(args.config_file)
    elif (args.oil_water):
        if (args.o is None):
            ff_id_name = "raw_" + args.oil_water
            output_filename = f"../output/martini/martini_{ff_id_name}.ff"
        else:
            output_filename = args.o
        
        match args.oil_water:
            case 'hexadecane':
                choosed_partition = HD_WN
            case 'octanol':
                choosed_partition = OCOS_WN
    else:
        print("Error no args")

    prep()