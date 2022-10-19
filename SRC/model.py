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

        barras, linhas, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = NetData(path_filename=self.data_dir,S_base=self.S_base,V_base=self.V_base).get_system_data()
        times = self.times

    # Criando o modelo
        
        # Pyomo Model     
        self.modelo  = pe.ConcreteModel()
        # Model name
        self.modelo.name = '*** Fluxo de Carga SOCP ***'
        # Propriedades
        mva = self.S_base
        solver = self.solver


    # Criando Variaveis de Decisao

        self.modelo.P_ij = pe.Var(linhas, linhas, times, domain=pe.Reals)  # purchased power
        self.modelo.Q_ij = pe.Var(linhas, linhas, times, domain=pe.Reals)  # purchased power
        self.modelo.I = pe.Var(linhas, linhas, times, domain=pe.Reals)
        self.modelo.V = pe.Var(linhas, times, domain=pe.Reals)
        self.modelo.Pgen = pe.Var(linhas, times, domain=pe.Reals)
        self.modelo.Qgen = pe.Var(linhas, times, domain=pe.Reals)
        self.modelo.Perdas = pe.Var(linhas, times, domain=pe.Reals)


        # _________ Variables initialization _________
        for t in times:
            for i in linhas:
                for j in linhas:
                    self.modelo.P_ij[i,j,t] = 0.0
                    self.modelo.Q_ij[i,j,t] = 0.0
                    self.modelo.I[i,j,t] = 0.0

                self.modelo.V[i,t] = 0.0
                self.modelo.Pgen[i,t] = 0.0
                self.modelo.Qgen[i,t] = 0.0
    
        # _________ Variable Bounds _________
        for t in times:
            for i in linhas:
                for j in linhas:
                    self.modelo.I[i,j,t].setub(500 ** 2)    # Square of the current magnitude
                    self.modelo.I[i,j,t].setlb(0 ** 2)
            
                self.modelo.V[i,t].setlb(0.95 ** 2)    # Square of the voltage magnitude
                self.modelo.V[i,t].setub(1.05 ** 2)

                self.modelo.Pgen[i,t].setlb(0)
                self.modelo.Pgen[i,t].setub(P_gen_limit[i])

                self.modelo.Qgen[i,t].setlb(0)
                self.modelo.Qgen[i,t].setub(Q_gen_limit[i])
        
        self.modelo.active_power = pe.ConstraintList()
        self.modelo.reactive_power = pe.ConstraintList()
        self.modelo.voltage_drop = pe.ConstraintList()
        self.modelo.branch_flow = pe.ConstraintList()
        self.modelo.perdas = pe.ConstraintList()
        
        for t in times:
            for i in linhas:
                self.modelo.perdas.add(self.modelo.Perdas[i,t] == self.modelo.Pgen[i,t]  - P[i])
                

            for i in linhas:
                # _________ (1) P = load - Pres + somaP + r * I^2 ________________________________________________________
                self.modelo.active_power.add(self.modelo.Pgen[i,t] - P[i] - 
                                    sum(R[i][j] * self.modelo.I[i,j,t] for j in linhas if j>i if Cx[i][j] == 1) + 
                                    sum(self.modelo.P_ij[i,j,t] for j in linhas if j>i if Cx[i][j] == 1) == 
                                    sum(self.modelo.P_ij[k,i,t] for k in linhas if k<i if Cx[k][i] == 1))


                # _________ (2) Q = load - Qres + somaQ + r * I^2 ________________________________________________________
                self.modelo.reactive_power.add(self.modelo.Qgen[i,t] - Q[i] - 
                                sum(X[i][j] * self.modelo.I[i,j,t] for j in linhas if j>i if Cx[i][j] == 1) + 
                                sum(self.modelo.Q_ij[i,j,t] for j in linhas if j>i if Cx[i][j] == 1) == 
                                sum(self.modelo.Q_ij[k,i,t] for k in linhas if k<i if Cx[k][i] == 1))

            for i in linhas:
                for j in linhas:
                    if Cx[i][j] == 1:
                        # _________ (3) Vm^2 - 2(r x P + x x Q) + (r^2 + x^2). I^2 = Vn ^2 ______________________________________
                        self.modelo.voltage_drop.add(self.modelo.V[i,t] == self.modelo.V[j,t] - 2 * (R[i][j] * self.modelo.P_ij[i,j,t] + X[i][j] * self.modelo.Q_ij[i,j,t]) +
                                            ((R[i][j]) ** 2 + (X[i][j]) ** 2) * self.modelo.I[i,j,t] )

                        # _________ (4) V^2 x I^2 = P^2 + Q^2 ___________________________________________________________________
                        self.modelo.branch_flow.add((self.modelo.V[i,t]) * self.modelo.I[i,j,t] >= (self.modelo.P_ij[i,j,t] ** 2) + (self.modelo.Q_ij[i,j,t] ** 2))


    # Resolução do Problema

        obj = sum(10*self.modelo.Pgen[i,t] for i in linhas for t in times)
        self.modelo.objective = pe.Objective(sense=pe.minimize, expr=obj)

        # Solve the problem
        solver = po.SolverFactory(solver)
        result = solver.solve(self.modelo)


         # Results
        V = {t:{i:0 for i in linhas} for t in times}
        I = {t:{i:{j:0 for j in linhas} for i in linhas} for t in times}
        P_ij = {t:{i:{j:0 for j in linhas} for i in linhas} for t in times}
        Q_ij = {t:{i:{j:0 for j in linhas} for i in linhas} for t in times}
        Pgen = {t:{i:0 for i in linhas} for t in times}
        Perdas = {t:{i:0 for i in linhas} for t in times}

        #region Pass results
        for t in times:
            for i in linhas:
                V[t][i] = pe.value(self.modelo.V[i,t]) ** 0.5
                Pgen[t][i] = pe.value(self.modelo.Pgen[i,t]) * mva
                Perdas[t][i] = pe.value(self.modelo.Perdas[i,t] * mva)
            
                for j in barras:
                    I[t][i][j] = pe.value(self.modelo.I[i,j,t]) ** 0.5
                    P_ij[t][i][j] = pe.value(self.modelo.P_ij[i,j,t]) * mva
                    Q_ij[t][i][j] = pe.value(self.modelo.Q_ij[i,j,t]) * mva
        #endregion
        P_ijt = {t:0 for t in times}
        for t in times:
            P_ijt[t] = sum(P_ij[t][i][j] for i in linhas for j in linhas)

        
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
    PF = SOCP_PF('DATA/teste.xlsx',100e3,13.8)
    PF.solve(print_output=True)
    