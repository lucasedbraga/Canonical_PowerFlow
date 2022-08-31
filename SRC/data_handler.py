import time
import pandas as pd
import math
import numpy

def read_data(path_filename, sheet, header, column_index):
    """
    First function to load the entire data from an excel file
    ---------------------------------------------------------
    Args:
        path_filename = 'str' to path file
        sheet = 'str' name of the sheet to open
        header = 'int' line of the header of the data
        column_index = 'int' column of the indices of the data
    ----------------------------------------------------------
    Return:
        DataFrame with the entire data labeled acording the excel
        file labels and indices
    """
    
    data = pd.ExcelFile(path_filename)
    data_ = pd.read_excel(data, sheet_name=sheet, header=header, index_col=column_index)

    return data_


def return_branch_data(file_path, sheet_name, sheet_name_agents):
    """
    Fetch data from .xlsx file from a specific sheet
    ------------------------------------------------
    Args: 
        file_path = 'str' to path file
        sheet_name = 'str' name of the sheet to open
    ------------------------------------------------
    Return:
        branches, nodes, P, Q, R, X, Pgen_limit, Qgen_limit
    """
    
    branch_data = read_data(file_path, sheet_name, header=0, column_index=0)
    agents_data = read_data(file_path, sheet_name_agents, header=0, column_index=0)
    column_index = branch_data.columns.values
    column_index_agents = agents_data.columns.values

    from_bus = branch_data[column_index[0]].values
    to_bus = branch_data[column_index[1]].values
    Resistance = branch_data[column_index[2]].values
    Reactance = branch_data[column_index[3]].values

    Bus_Location = agents_data[column_index_agents[0]].values
    ActivePower = agents_data[column_index_agents[1]].values
    ReactivePower = agents_data[column_index_agents[2]].values
    P_gen = agents_data[column_index_agents[3]].values
    Q_gen = agents_data[column_index_agents[4]].values

    nodes = list(range(1,len(from_bus)+2))

    P, P_gen_limit = {},{}
    Q, Q_gen_limit = {},{}
    R = {i:{j:0 for j in nodes} for i in nodes}
    X = {i:{j:0 for j in nodes} for i in nodes}
    branches  = {}
    head_bus, tails = [], []

    for pos in range(0,len(from_bus)):
        R[from_bus[pos]][to_bus[pos]] = Resistance[pos]
        R[to_bus[pos]][from_bus[pos]] = Resistance[pos]
        X[from_bus[pos]][to_bus[pos]] = Reactance[pos]
        X[to_bus[pos]][from_bus[pos]] = Reactance[pos]

    for pos in range(1, len(from_bus)+1):
        branches[pos] = (int(from_bus[pos-1]),int(to_bus[pos-1]))

        head_bus.append(from_bus[pos-1])
        tails.append(to_bus[pos-1])

    for loc in Bus_Location:
        P[loc] = ActivePower[loc-1]
        Q[loc] = ReactivePower[loc-1]
        P_gen_limit[loc] = P_gen[loc-1]
        Q_gen_limit[loc] = Q_gen[loc-1]

    Cx = {n:{nn:0 for nn in nodes} for n in nodes}
    for i in nodes:
        for j in nodes:
            if R[i][j] != 0:
                Cx[i][j] = 1

    head_bus = list(dict.fromkeys(head_bus))

    # Set of tail buses on head buses
    tail_bus = {head:[] for head in head_bus}

    for head in head_bus:
        for tail in tails:
            if (head,tail) in branches:
                tail_bus[head].append(tail)


    return branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx


def convert_power_pu(power_kw, mva):
    """
    Convert Dictionary Data in kW to p.u.
    -------------------------------------
    Args:
        power_pw = 'dict' with data in kW
        mva = 'int' base power in MVA
    -------------------------------------
    Return:
        Dict with same structure data in p.u.
    -------------------------------------
    Formula: https://nepsi.com/resources/calculators/per-unit-impedance-calculator.htm
    """

    
    if type(power_kw[1]) is not dict:
        agents = power_kw.keys()
        power_pu = {a:0 for a in agents}

        for a in agents:
                if math.isnan(power_kw[a]):
                    power_pu[a] = 0
                else:
                    power_pu[a] = power_kw[a]/(mva*1000)
    else:
        time_interval = power_kw.keys()
        agents = power_kw[1].keys()
        power_pu = {t:{a:0 for a in agents} for t in time_interval}
        
        for t in time_interval:
            for a in agents:
                if math.isnan(power_kw[t][a]):
                    power_pu[t][a] = 0
                else:
                    power_pu[t][a] = power_kw[t][a]/(mva*1000)

    return power_pu


def convert_ohm_pu(z_ohm, mva, kv):
    """
    Convert Dictionary Data in ohm to p.u.
    -------------------------------------
    Args:
        power_pw = 'dict' with data in kW
        mva = 'int' base power in MVA
        kv = 'int' power transformer voltage level
    -------------------------------------
    Return:
        Dict with same structure data in p.u.
    -------------------------------------
    Formula: https://nepsi.com/resources/calculators/per-unit-impedance-calculator.htm
    """
    nodes = list(z_ohm.keys())
    z_pu = {i:{j:0 for j in nodes} for i in nodes}

    z_base = (kv * kv ) / (mva)
    
    for i in nodes:
        for j in nodes:
            z_pu[i][j] = z_ohm[i][j]/z_base

    return z_pu


def scaling_data(data, scale=int):
    """
    Scaling of data for the model
    -----------------------------
    Args:
        data = 'dict' with data to be scaled
        scale = 'int' with the scale wanted
    -----------------------------
    Return:
        Dict with same structure with the scaled data
    """

    if type(data[1]) is not dict:
        data = {n:data[n]*scale for n in data.keys()}
    else:
        data = {t:{n:data[t][n]*scale for n in data[t].keys()} for t in data.keys()} 

    return data


def discaling_data(data, scale=int):
    """
    Discaling of data after the model
    -----------------------------
    Args:
        data = 'dict' with data to be scaled
        scale = 'int' with the scale wanted
    -----------------------------
    Return:
        Dict with same structure with the discaled data
    """

    if type(data[1]) is not dict:
        data = {n:data[n]/scale for n in data.keys()}
    else:
        data = {t:{n:data[t][n]/scale for n in data[t].keys()} for t in data.keys()} 

    return data