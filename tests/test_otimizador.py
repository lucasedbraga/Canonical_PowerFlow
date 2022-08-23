import pyomo.environ as pyo
from pyomo.environ import *
from pyomo.opt import SolverFactory


def test_otimizador_mindtpy_inteiro():

    model = pyo.ConcreteModel()

    model.x = pyo.Var(within=Integers, bounds=(0,10))
    model.y = pyo.Var(bounds=(0,10))
    x = model.x
    y = model.y

    model.C1 = pyo.Constraint(expr= -x+2*y*x <= 8)
    model.C2 = pyo.Constraint(expr= 2*x + y <= 14)
    model.C3 = pyo.Constraint(expr= 2*x - y <= 10)

    model.obj = pyo.Objective(expr= -(x*y))

    opt = SolverFactory('mindtpy')
    opt.solve(model,mip_solver='glpk', nlp_solver='ipopt')
    model.pprint()

    x_value = pyo.value(x)
    y_value = pyo.value(y)

    assert x_value == 5

def test_otimizador_mindtpy_continuo():

    model = pyo.ConcreteModel()

    model.x = pyo.Var(within=Integers, bounds=(0,10))
    model.y = pyo.Var(bounds=(0,10))
    x = model.x
    y = model.y

    model.C1 = pyo.Constraint(expr= -x+2*y*x <= 8)
    model.C2 = pyo.Constraint(expr= 2*x + y <= 14)
    model.C3 = pyo.Constraint(expr= 2*x - y <= 10)

    model.obj = pyo.Objective(expr= -(x*y))

    opt = SolverFactory('mindtpy')
    opt.solve(model,mip_solver='glpk', nlp_solver='ipopt')
    model.pprint()

    x_value = pyo.value(x)
    y_value = pyo.value(y)

    erro = y_value - 1.300000012498684
    assert erro < 0.00001