import pandas as pd

df = pd.read_excel('DATA/teste.xlsx', sheet_name='Branch_data')
with open('outputs/DATA.json','w') as f:
    f.write(str(df.to_json()))