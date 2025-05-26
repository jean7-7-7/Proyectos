import pandas as ps
import matplotlib.pyplot as plt
import missingno as msno
#Cargamos el dataset 
var= "/storage/emulated/0/Download/archive/googleplaystore.csv"
db= ps.read_csv(var, index_col= False)

#Se buscan valores nulos, se eliminan y se sustituyen valores extraños

msno.matrix(db)
plt.show()

db_drop= db.dropna()
db_drop.loc[db_drop["Rating"]>5,"Rating"]=5

# ¿Que categorias tienen mejor Rating?

df= db_drop[["Category","Rating"]].groupby(by="Category").sum().sort_values("Rating", ascending= False)
print(df.head(10))

#Agregamos y unimos la siguente tabla para un analisis mas preciso reseñas

db_reviews= ps.read_csv("/storage/emulated/0/Download/archive/googleplaystore_user_reviews.csv",index_col=False).dropna()

join= ps.merge(db_drop,db_reviews, on= "App")

#Ordenamos la tabla para un mejor analisis y eliminanos los valores que no aportan informacion relevante

join_sort=join[["Sentiment","Sentiment_Polarity","Content Rating"]].groupby(by=["Content Rating","Sentiment"]).size().unstack(fill_value= 0).drop("Adults only 18+", errors="ignore")
print(join_sort)

# Graficamos

join_sort.plot(kind='bar', stacked=True, figsize=(10, 6), colormap='viridis')
plt.title('Distribución de Sentimientos por Rating de Contenido')
plt.xlabel('Rating de Contenido')
plt.ylabel('Cantidad')
plt.xticks(rotation=45)
plt.legend(title='Sentimiento')
plt.tight_layout()

plt.show()