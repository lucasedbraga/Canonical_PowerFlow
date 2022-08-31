import pyomo.environ as pe
import pyomo.opt as po


def create_model_PF(branches, nodes, time):
    
    # model creation
    m  = pe.ConcreteModel()

    # model name
    m.name = '*** Branch Flow no SOCP ***'

    #region Sets
    # Set of Branches
    m.branches = branches

    # Set of total nodes
    m.nodes = nodes

    # Set of time interval
    m.time = time

    return m


def create_decision_variables_PF(m, P_gen_limit, Q_gen_limit):

    m.P_ij = pe.Var(m.nodes, m.nodes, m.time, domain=pe.Reals)  # purchased power
    m.Q_ij = pe.Var(m.nodes, m.nodes, m.time, domain=pe.Reals)  # purchased power
    m.I = pe.Var(m.nodes, m.nodes, m.time, domain=pe.Reals)
    m.V = pe.Var(m.nodes, m.time, domain=pe.Reals)
    m.Pgen = pe.Var(m.nodes, m.time, domain=pe.Reals)
    m.Qgen = pe.Var(m.nodes, m.time, domain=pe.Reals)
    m.Perdas = pe.Var(m.nodes, m.time, domain=pe.Reals)

    # _________ Variables initialization _________
    for t in m.time:
        for i in m.nodes:
            for j in m.nodes:
                m.P_ij[i,j,t] = 0.0
                m.Q_ij[i,j,t] = 0.0
                m.I[i,j,t] = 0.0

            m.V[i,t] = 0.0
            m.Pgen[i,t] = 0.0
            m.Qgen[i,t] = 0.0
    
    # _________ Variable Bounds _________
    for t in m.time:
        for i in m.nodes:
            for j in m.nodes:
                m.I[i,j,t].setub(500 ** 2)    # Square of the current magnitude
                m.I[i,j,t].setlb(0 ** 2)
        
            m.V[i,t].setlb(0.95 ** 2)    # Square of the voltage magnitude
            m.V[i,t].setub(1.05 ** 2)

            m.Pgen[i,t].setlb(0)
            m.Pgen[i,t].setub(P_gen_limit[i])

            m.Qgen[i,t].setlb(0)
            m.Qgen[i,t].setub(Q_gen_limit[i])

    return m


def create_constraints_PF(m, R, X, P, Q, Cx):

    m.active_power = pe.ConstraintList()
    m.reactive_power = pe.ConstraintList()
    m.voltage_drop = pe.ConstraintList()
    m.branch_flow = pe.ConstraintList()
    m.perdas = pe.ConstraintList()
    
    for t in m.time:
        for i in m.nodes:
            m.perdas.add(m.Perdas[i,t] == m.Pgen[i,t]  - P[i])
            

        for i in m.nodes:
            # _________ (1) P = load - Pres + somaP + r * I^2 ________________________________________________________
            m.active_power.add(m.Pgen[i,t] - P[i] - 
                                sum(R[i][j] * m.I[i,j,t] for j in m.nodes if j>i if Cx[i][j] == 1) + 
                                sum(m.P_ij[i,j,t] for j in m.nodes if j>i if Cx[i][j] == 1) == 
                                sum(m.P_ij[k,i,t] for k in m.nodes if k<i if Cx[k][i] == 1))


            # _________ (2) Q = load - Qres + somaQ + r * I^2 ________________________________________________________
            m.reactive_power.add(m.Qgen[i,t] - Q[i] - 
                            sum(X[i][j] * m.I[i,j,t] for j in m.nodes if j>i if Cx[i][j] == 1) + 
                            sum(m.Q_ij[i,j,t] for j in m.nodes if j>i if Cx[i][j] == 1) == 
                            sum(m.Q_ij[k,i,t] for k in m.nodes if k<i if Cx[k][i] == 1))

        for i in m.nodes:
            for j in m.nodes:
                if Cx[i][j] == 1:
                    # _________ (3) Vm^2 - 2(r x P + x x Q) + (r^2 + x^2). I^2 = Vn ^2 ______________________________________
                    m.voltage_drop.add(m.V[i,t] == m.V[j,t] - 2 * (R[i][j] * m.P_ij[i,j,t] + X[i][j] * m.Q_ij[i,j,t]) +
                                        ((R[i][j]) ** 2 + (X[i][j]) ** 2) * m.I[i,j,t] )

                    # _________ (4) V^2 x I^2 = P^2 + Q^2 ___________________________________________________________________
                    m.branch_flow.add((m.V[i,t]) * m.I[i,j,t] >= (m.P_ij[i,j,t] ** 2) + (m.Q_ij[i,j,t] ** 2))


    return m


def solve_problem_PF(m, solver_, print_output=bool, mva=int):

    obj = sum(10*m.Pgen[i,t] for i in m.nodes for t in m.time)

    m.objective = pe.Objective(sense=pe.minimize, expr=obj)

    # Solve the problem
    solver = po.SolverFactory(solver_)
    result = solver.solve(m)

    # Results
    V = {t:{i:0 for i in m.nodes} for t in m.time}
    I = {t:{i:{j:0 for j in m.nodes} for i in m.nodes} for t in m.time}
    P_ij = {t:{i:{j:0 for j in m.nodes} for i in m.nodes} for t in m.time}
    Q_ij = {t:{i:{j:0 for j in m.nodes} for i in m.nodes} for t in m.time}
    Pgen = {t:{i:0 for i in m.nodes} for t in m.time}
    Perdas = {t:{i:0 for i in m.nodes} for t in m.time}
    #region Pass results
    for t in m.time:
        for i in m.nodes:
            V[t][i] = pe.value(m.V[i,t]) ** 0.5
            Pgen[t][i] = pe.value(m.Pgen[i,t]) * mva
            Perdas[t][i] = pe.value(m.Perdas[i,t] * mva)
        
            for j in m.branches:
                I[t][i][j] = pe.value(m.I[i,j,t]) ** 0.5
                P_ij[t][i][j] = pe.value(m.P_ij[i,j,t]) * mva
                Q_ij[t][i][j] = pe.value(m.Q_ij[i,j,t]) * mva
    #endregion
    P_ijt = {t:0 for t in m.time}
    for t in m.time:
        P_ijt[t] = sum(P_ij[t][i][j] for i in m.nodes for j in m.nodes)

    

    #region Output
    if result.solver.status == po.SolverStatus.ok:
        print('Model: ',m.name)
        print('[INFO] Results:')
        print('\t> [SUCCESS] The problem converged!')
        if print_output:
            print('\n> P_ij [kW]:',P_ij)
            print('\n> Q_ij [kVAr]:',Q_ij)
            print('\n> V [pu]:',V)
            print('\n> I [pu]:',I)
            print('\n> Pgen [kW]:',Pgen)
            print("\t> Optimal point:", round(pe.value(m.objective), 3))
            print("--------------------------------------------------------------------------------------------------------------")
            print()
            print("Sum Pij:",P_ijt)
            print("Perdas", Perdas)
            perdas_totais = 0
            for barra in Perdas[1].keys():
                perdas_totais += Perdas[1][barra]
            print("Perdas Totais", perdas_totais)

    else:
        print('[ERROR] Did not converge!')
    #endregion

    return P_ij, Q_ij, V, I
