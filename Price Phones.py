import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor

#Importamos los datos
db=pd.read_csv("ndtv_data_final.csv")
#Variable categorica a numerica
db["modelos_num"]=pd.factorize(db["Brand"])[0]

df=db[["Battery capacity (mAh)", "Screen size (inches)", "RAM (MB)","Internal storage (GB)", "Rear camera","Front camera","Processor","modelos_num","Resolution x","Resolution y","Price"]].sample()
#Datos Explicativos 
db_exp=df[["Battery capacity (mAh)", "Screen size (inches)", "RAM (MB)","Internal storage (GB)", "Rear camera","Front camera","Processor","modelos_num","Resolution x","Resolution y"]]

#Preparamos los modelos

#En "X"  las variables determinantes y en "Y" lo que queremos obtener

x=db[["Battery capacity (mAh)", "Screen size (inches)", "RAM (MB)","Internal storage (GB)", "Rear camera","Front camera","Processor","modelos_num","Resolution x","Resolution y"]]

y= db["Price"]

X_train, X_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42)

#Seleccionamos el modelo lineal
modelo= LinearRegression()
modelo.fit(X_train, y_train)

print(f"El puntaje de calidad del modelo lineal es: {modelo.score(X_test, y_test)}")

#Seleccionamos el modelo forest

modelo_forest= RandomForestRegressor(n_estimators= 1000, random_state= 42)
modelo_forest.fit(X_train, y_train)
pts=modelo_forest.score(X_test, y_test)
print(f"El puntaje de calidad del modelo Forest es: {pts}")

cualidades= pd.DataFrame(db_exp, columns= ["Battery capacity (mAh)", "Screen size (inches)", "RAM (MB)","Internal storage (GB)", "Rear camera","Front camera","Processor","modelos_num","Resolution x","Resolution y"])
exito= modelo_forest.predict(cualidades)[0]

print(f"Dadas las siguientes caractetisticas:{cualidades}, su precio estimado seria un aproximado de {exito}$")
