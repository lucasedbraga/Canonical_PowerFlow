from matplotlib.dates import ConciseDateConverter
import pyomo.environ as pe
import pyomo.opt as po
from data_handler import NetData
from pprint import pprint, pformat
import contextlib

class SOCP_PF:

    def __init__(self, data_dir, S_base, V_base, solver='ipopt', times=1):
        
        self.data_dir = data_dir
        self.S_base = S_base
        self.V_base = V_base
        self.solver = solver
        self.times = range(times)

        
    def solve(self, print_output:bool = False):

        linhas, barras, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = NetData(path_filename=self.data_dir,S_base=self.S_base,V_base=self.V_base).get_system_data()

    # Criando o modelo
        
        # Pyomo Model     
        self.modelo  = pe.ConcreteModel()
        # Model name
        self.modelo.name = '*** Fluxo de Carga SOCP ***'
        # Propriedadesa
        mva = self.S_base
        solver = self.solver


    # Criando Variaveis de Decisao

        self.modelo.P_ij = pe.Var(barras, barras, domain=pe.Reals)  # purchased power
        self.modelo.Q_ij = pe.Var(barras, barras, domain=pe.Reals)  # purchased power
        self.modelo.I = pe.Var(barras, barras, domain=pe.Reals)
        self.modelo.V = pe.Var(barras, domain=pe.Reals)
        self.modelo.Pgen = pe.Var(barras, domain=pe.Reals)
        self.modelo.Qgen = pe.Var(barras, domain=pe.Reals)
        self.modelo.Perdas = pe.Var(barras, domain=pe.Reals)
        self.modelo.P_tiu = pe.Var(barras, domain=pe.Reals)


        # _________ Variables initialization _________
        for i in barras:
            for j in barras:
                self.modelo.P_ij[i,j] = 0.0
                self.modelo.Q_ij[i,j] = 0.0
                self.modelo.I[i,j] = 0.0

            self.modelo.V[i] = 0.0
            self.modelo.Pgen[i] = 0.0
            self.modelo.Qgen[i] = 0.0
            self.modelo.Perdas[i] = 0.0
            self.modelo.P_tiu[i] = 0.0
    
        # _________ Variable Bounds _________
        for i in barras:
            for j in barras:
                self.modelo.I[i,j].setub(500 ** 2)    # Square of the current magnitude
                self.modelo.I[i,j].setlb(0 ** 2)
        
            self.modelo.V[i].setlb(0.95 ** 2)    # Square of the voltage magnitude
            self.modelo.V[i].setub(1.05 ** 2)

            self.modelo.Pgen[i].setlb(0)
            self.modelo.Pgen[i].setub(P_gen_limit[i])

            self.modelo.Qgen[i].setlb(0)
            self.modelo.Qgen[i].setub(Q_gen_limit[i])
        
        self.modelo.balanco_p = pe.ConstraintList()
        self.modelo.balanco_q = pe.ConstraintList()
        self.modelo.queda_tensao = pe.ConstraintList()
        self.modelo.balanco_perdas = pe.ConstraintList()
        self.modelo.ptiu_perdas = pe.ConstraintList()     
        self.modelo.inequation = pe.ConstraintList()
           

        for i in barras:
            # _________ (1) Pg - Pd - (somaPij + Pperdas) == 0 ________________________________________________________
            self.modelo.balanco_p.add(self.modelo.Pgen[i] - P[i] - ( 
                                sum(R[i][j] * self.modelo.I[i,j]**2 for j in barras if j>i if Cx[i][j] == 1) + 
                                sum(self.modelo.P_ij[i,j] for j in barras if j>i if Cx[i][j] == 1) -
                                sum(self.modelo.P_ij[k,i] for k in barras if k<i if Cx[k][i] == 1))
                                ==0)


            # _________ (2) Qg - Qd - (somaQij + Qperdas) == 0 ________________________________________________________
            self.modelo.balanco_q.add(self.modelo.Qgen[i ] - Q[i] - (
                                sum(X[i][j] * self.modelo.I[i,j]**2 for j in barras if j>i if Cx[i][j] == 1) + 
                                sum(self.modelo.Q_ij[i,j ] for j in barras if j>i if Cx[i][j] == 1) -
                                sum(self.modelo.Q_ij[k,i ] for k in barras if k<i if Cx[k][i] == 1))
                                == 0)
            

        for i in barras:
            for j in barras:
                if Cx[i][j] == 1:

                    # _________ (3) 2(R*P + X*Q) + (R^2 + X^2). I^2 - somaV^2 == 0 ______________________________________
                    self.modelo.queda_tensao.add(0 == self.modelo.V[j] - (self.modelo.V[i] + (2 * (R[i][j] * self.modelo.P_ij[i,j] + X[i][j] * self.modelo.Q_ij[i,j])) +
                                ((R[i][j]) ** 2 + (X[i][j]) ** 2) * self.modelo.I[i,j]**2))

                    # _________ (4) CXP - CRQ ==  0 ________________________________________________________
                    self.modelo.balanco_perdas.add(X[i][j] * self.modelo.P_ij[i,j]  - R[i][j] * self.modelo.Q_ij[i,j] == 0)

                    # _________ (5) R*i^2 = 2*R*~P ___________________________________________________________________
                    self.modelo.ptiu_perdas.add(R[i][j]*self.modelo.I[i,j]**2 - 2*R[i][j]*self.modelo.P_tiu[i] == 0)

                    # _________ (6) ~P*V^2 >= P^2 + Q^2 ___________________________________________________________________
                    self.modelo.inequation.add((self.modelo.P_tiu[i] * (self.modelo.V[i]**2)) >= (self.modelo.P_ij[i,j] ** 2) + (self.modelo.Q_ij[i,j] ** 2))


    # Resolução do Problema

        obj = sum(self.modelo.P_tiu[i]  for i in barras)
        self.modelo.objective = pe.Objective(sense=pe.minimize, expr=obj)

        # Solve the problem
        solver = po.SolverFactory(solver)
        result = solver.solve(self.modelo)


         # Results
        V = {i:0 for i in barras}
        I = {i:{j:0 for j in barras} for i in barras}
        P_ij = {i:{j:0 for j in barras} for i in barras}
        Q_ij = {i:{j:0 for j in barras} for i in barras}
        Pgen = {i:0 for i in barras}
        Perdas = {i:0 for i in barras}

        #region Pass results

        for i in barras:
            V[i] = pe.value(self.modelo.V[i]) ** 0.5
            Pgen[i] = pe.value(self.modelo.Pgen[i]) * mva
            Perdas[i] = pe.value(self.modelo.Perdas[i] * mva)
        
            for j in linhas:
                I[i][j] = pe.value(self.modelo.I[i,j]) ** 0.5
                P_ij[i][j] = pe.value(self.modelo.P_ij[i,j]) * mva
                Q_ij[i][j] = pe.value(self.modelo.Q_ij[i,j]) * mva
        #endregion
        P_ijt= sum(P_ij[i][j] for i in barras for j in barras)

        
        #region Output
        if result.solver.status == po.SolverStatus.ok:
            print('Model: ',self.modelo.name)
            print('[INFO] Results:')
            print('\t> [SUCCESS] The problem converged!')
            if print_output:

                print(f"\n> P_ij [kW]:")
                pprint({'Fluxo P': P_ij})

                print(f"\n> Q_ij [kVAr]:")
                pprint({'Fluxo Q': Q_ij})

                print(f"\n> V [pu]:")
                pprint({'Tensões': V})

                print(f"\n> I [pu]:")
                pprint({'Correntes': I})

                print(f"\n> Pgen [kW]:")
                pprint({'PotGerador': Pgen})

                print("\t> Optimal point:", round(pe.value(self.modelo.objective), 3))
                print("--------------------------------------------------------------------------------------------------------------")
                print()

                print(f"Sum Pij:")
                pprint({'Somatorio FluxPot': P_ijt})

                print(f"Perdas:")
                pprint({'Perdas':Perdas})
                
                perdas_totais = 0
                # for barra in Perdas.keys():
                #     perdas_totais += Perdas[barra]
                # print("Perdas Totais", perdas_totais)

        else:
            print('[ERROR] Did not converge!')
        #endregion

        with open('outputs/resolution.txt','w') as f:
            with contextlib.redirect_stdout(f):
                self.modelo.pprint()


        with open('outputs/output.json','w') as f:
            f.write(pformat({'Fluxo P': P_ij}))
            f.write(pformat({'Fluxo Q': Q_ij}))
            f.write(pformat({'Tensões': V}))
            f.write(pformat({'Correntes': I}))
            f.write(pformat({'PotGerador': Pgen}))
            f.write(pformat({'Somatorio FluxPot': P_ijt}))
            f.write(pformat({'Perdas':Perdas}))
            #f.write(f"Perdas Totais = {perdas_totais}")



        return P_ij, Q_ij, V, I


if __name__ == '__main__':
    PF = SOCP_PF('DATA/teste.xlsx',S_base=100, V_base=13.8)
    # PF = SOCP_PF('DATA/teste.xlsx',S_base=100e-3, V_base=12.66)
    PF.solve(print_output=True)
    