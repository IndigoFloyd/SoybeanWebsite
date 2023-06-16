import pandas as pd

CommonNameDict = {}
CommonNameList = []
with open("USDAaccessionCommonName.txt", encoding='utf-8') as r:
    lines = r.readlines()[1:]
    for line in lines:
        tmp = line.split('\t')
        CommonName = tmp[1].strip().replace('(', '').replace(')', '')
        PI = tmp[0]
        if CommonNameDict.get(PI):
            CommonNameDict[PI] = CommonNameDict.get(PI, '') + ';' + CommonName
        else:
            CommonNameDict[PI] = CommonName

for key, value in CommonNameDict.items():
    newDict = {"acid": key, "CommonName": str(value)}
    CommonNameList.append(newDict)
df = pd.read_csv(r"D:\QQFile\1135431747\FileRecv\25.csv")
df.set_index('acid', inplace=True)
df1 = pd.DataFrame(CommonNameList)
df1.set_index('acid', inplace=True)
df_concat = pd.concat([df, df1], axis=1, join='outer')
df_concat.to_csv("data.csv")
# for i in range(len(df_concat)):
#     if not pd.isna(df_concat.iloc[i, -1]):
#         print(df_concat.iloc[i, -1])
#         print(df_concat.iloc[i, 1:-1])