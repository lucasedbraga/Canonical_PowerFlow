import sys
sys.path.append('SRC')
from data_handler import NetData


def test_NetData_class():
    obj = NetData('DATA/teste.xlsx')
    assert obj.S_base == 100e3
    assert obj.V_base == 13.8
    assert obj.Ybar == None

def test_get_system_data():
    def arredonda_ohm_pu(dict_value):
        for key in dict_value.keys():
            for k, v in dict_value[key].items():
                dict_value[key][k] = round(v, 2)
        return dict_value


    expected = {
        "Linhas": {1:(1,2)},
        "Barras": [1,2],
        "P": {1:0, 2:0.4},
        "Q": {1:0,2:0},
        "R": {1: {1: 0.0, 2: 0.2}, 2: {1: 00.2, 2: 0.0}},
        "X": {1: {1:0.0, 2: 1}, 2: {1: 1, 2: 0.0}},
        "P_gen_limit": {1:100,2:0},
        "Q_gen_limit": {1:100,2:0},
    }

    branches, nodes, P, Q, R, X, P_gen_limit, Q_gen_limit, Cx = NetData('DATA/teste.xlsx').get_system_data()
    
    assert branches == expected["Linhas"]
    assert nodes == expected["Barras"]
    assert P == expected["P"]
    assert Q == expected["Q"]
    assert arredonda_ohm_pu(R) == expected["R"]
    assert arredonda_ohm_pu(X) == expected["X"]
    assert P_gen_limit == expected["P_gen_limit"]
    assert Q_gen_limit == expected["Q_gen_limit"]


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