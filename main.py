from SRC import data_handler, SOCP_PF

ramos, nos, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = data_handler.return_branch_data('DATA/ieee-33.xlsx','Branch_data','Branch_loads')
P = data_handler.convert_power_pu(P,100)
P_gen_limit = data_handler.convert_power_pu(P_gen_limit,100)
Q = data_handler.convert_power_pu(Q,100)
Q_gen_limit = data_handler.convert_power_pu(Q_gen_limit,100)
R = data_handler.convert_ohm_pu(R,100,13.8)
X = data_handler.convert_ohm_pu(X,100,13.8)


modelo = SOCP_PF.create_model_PF(ramos,nos,{1,1})
SOCP_PF.create_decision_variables_PF(modelo,P_gen_limit,Q_gen_limit)
SOCP_PF.create_constraints_PF(modelo, R, X, P, Q, Cx)
SOCP_PF.solve_problem_PF(modelo,'ipopt', mva=100)