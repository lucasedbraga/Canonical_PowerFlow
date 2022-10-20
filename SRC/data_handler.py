import time
import pandas as pd
import math
import numpy as np


class NetData:


    def __init__(self, path_filename, S_base=100, V_base=13.8):
        
        self.data = pd.ExcelFile(path_filename)
        self.S_base = S_base*1e3
        self.V_base = V_base
        self.Ybar = None

    @staticmethod
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
                        power_pu[a] = power_kw[a]/(mva)
        else:
            time_interval = power_kw.keys()
            agents = power_kw[1].keys()
            power_pu = {t:{a:0 for a in agents} for t in time_interval}
            
            for t in time_interval:
                for a in agents:
                    if math.isnan(power_kw[t][a]):
                        power_pu[t][a] = 0
                    else:
                        power_pu[t][a] = power_kw[t][a]/(mva)

        return power_pu

    @staticmethod
    def convert_ohm_pu(z_ohm, mva, kv):
        """
        Convert Dictionary Data in ohm to p.u.
        -------------------------------------
        Args:
            z_ohm = 'dict' with data in Ohm
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


    @staticmethod
    def get_data(df,num_coluna):
        column_index = df.columns.values
        value = df[column_index[num_coluna]].values
        value = map(lambda x: x if x != 'x' else math.nan, value)
        return list(value)

    def get_system_data(self):
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
        
        DLIN_data = pd.read_excel(self.data, sheet_name ='DLIN',header=0, index_col=0)
        DBAR_data = pd.read_excel(self.data, sheet_name ='DBAR',header=0, index_col=0)
        column_index = DLIN_data.columns.values
        column_index_agents = DBAR_data.columns.values

        from_bus = self.get_data(DLIN_data,0)
        to_bus = self.get_data(DLIN_data,1)
        Resistance = self.get_data(DLIN_data,2)
        Reactance = self.get_data(DLIN_data,3)
        Bsh = self.get_data(DLIN_data,4)

        Bus_Location = self.get_data(DBAR_data,0)
        ActivePower = self.get_data(DBAR_data,1)
        ReactivePower = self.get_data(DBAR_data,2)
        P_gen = self.get_data(DBAR_data,3)
        Q_gen = self.get_data(DBAR_data,4)

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
            P[loc] = float(ActivePower[loc-1])
            Q[loc] = float(ReactivePower[loc-1])
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

        P = self.convert_power_pu(P,self.S_base) #Carga
        P_gen_limit = self.convert_power_pu(P_gen_limit,self.S_base) #Capacidade Ger Max
        Q = self.convert_power_pu(Q,self.S_base) # Reativo
        Q_gen_limit = self.convert_power_pu(Q_gen_limit,self.S_base) #Capacidade de Reativo
        R = self.convert_ohm_pu(R,mva=self.S_base,kv=self.V_base) # Resistencia
        X = self.convert_ohm_pu(X,mva=self.S_base,kv=self.V_base) # Reatancia

        
        return branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx




if __name__ == '__main__':
    from pprint import pprint, pformat
    branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = NetData('DATA/teste.xlsx').get_system_data()
    variables = [branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx]
    name = ['Linhas', 'Barras', 'P', 'Q', 'R', 'X', 'P_gen_limit', 'Q_gen_limit', 'Cx']
    for v in range(len(variables)):
        print(name[v])
        pprint(variables[v])
    
    with open('outputs/System_Data.json','w') as f:
        f.write(pformat({"Linhas": branches}))
        f.write(pformat({"Linhas": nodes}))
        f.write(pformat({"P": P}))
        f.write(pformat({"Q": Q}))
        f.write(pformat({"R": R}))
        f.write(pformat({"X": X}))
        f.write(pformat({"PGEN_limit": P_gen_limit}))
        f.write(pformat({"QGEN_limit": Q_gen_limit}))
        f.write(pformat({"Cx": Cx}))
