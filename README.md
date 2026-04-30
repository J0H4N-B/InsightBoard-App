# 📊 Dashboard de Análisis de Producto

Dashboard interactivo que permite subir cualquier CSV y explorar sus datos
a través de 4 tipos de gráficos configurables: barras, donut, líneas y dispersión.

## 🛠️ Stack

| Capa       | Tecnología                       |
|------------|----------------------------------|
| Backend    | Python 3.9+ · Flask · Blueprints |
| Datos      | Pandas · CSV                     |
| Frontend   | HTML · CSS · JavaScript          |
| Gráficos   | Chart.js 4                       |
| Iconos     | Boxicons                         |
| Seguridad  | Werkzeug · python-dotenv         |

## 🚀 Instalación

```bash
git clone https://github.com/J0H4N-B/dashboard-analisis-producto.git
cd dashboard-analisis-producto

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env       # Edita SECRET_KEY

python run.py
# http://localhost:5000
```

## 📁 Estructura

```
proyecto3_dashboard/
├── run.py
├── config.py
├── requirements.txt
├── .env.example
├── data/
│   ├── samples/
│   │   └── productos_ejemplo.csv
│   └── uploads/
├── app/
│   ├── __init__.py
│   ├── blueprints/
│   │   ├── main.py
│   │   ├── upload.py
│   │   └── dashboard.py
│   └── utils/
│       └── file_handler.py
└── templates/
    └── index.html
```

## ✨ Funcionalidades

- **Upload dinámico** — arrastra o selecciona cualquier CSV
- **Auto-configuración** — detecta columnas numéricas y categóricas automáticamente
- **4 gráficos interactivos** — barras, donut, líneas y dispersión, todos configurables
- **Filtros dinámicos** — multiselect por cada columna categórica del CSV
- **KPIs en tiempo real** — sumas de las métricas numéricas según filtros activos
- **CSV de ejemplo** — descargable desde la interfaz

## 🔒 Seguridad

- Solo `.csv` permitido · nombre sanitizado con UUID
- Ruta del archivo en sesión del servidor
- Límite de 5 MB y 50 000 filas configurable en `.env`
- Columnas validadas contra el DataFrame real

## 📄 Licencia

MIT
