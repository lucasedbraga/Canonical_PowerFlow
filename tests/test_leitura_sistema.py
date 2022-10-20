import sys
sys.path.append('SRC')
from data_handler import NetData


def test_NetData_class():
    obj = NetData('DATA/teste.xlsx')
    assert obj.S_base == 100e3
    assert obj.V_base == 13.8
    assert obj.Ybar == None

# def test_get_system_data():
#     branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = NetData('DATA/teste.xlsx').get_system_data()

def test_convert_power_pu():
    obj = NetData('DATA/teste.xlsx')
    power = {1: -40e3}
    pu = obj.convert_power_pu(power_kw=power, mva=100e3)
    assert pu[1] == -0.4

def test_convert_ohm_pu():
    obj = NetData('DATA/teste.xlsx')
    z = {1: {1: 0.00038088}}
    pu = obj.convert_ohm_pu(z_ohm=z,mva=100e3,kv=13.8)
    tol = 1e-3
    erro = abs(0.19999999999999996 - pu[1][1])    
    print(pu)
    assert erro < tol