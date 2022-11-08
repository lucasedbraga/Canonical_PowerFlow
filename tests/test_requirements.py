
def test_NetData_class():
    try:
        import sys
        sys.path.append('SRC')
        from data_handler import NetData
        obj = NetData('DATA/teste.xlsx')
    except:
        obj = None
    assert obj != None