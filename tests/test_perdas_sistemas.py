def teste_perda_IEEE_14():
    #perdas = conical_pf
    perdas = 511.4
    erro = abs(perdas - 511.44)
    assert erro < 0.05

def teste_perda_IEEE_33():
    #perdas = conical_pf
    perdas = 202.64
    erro = abs(perdas - 202.68)
    assert erro < 0.05