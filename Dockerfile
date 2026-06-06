# Dockerfile

# Folosim python:3.11-slim ca bază — lightweight și compatibil cu toate dependențele
FROM python:3.11-slim

# Setăm directorul de lucru în container
WORKDIR /app

# Instalăm dependențele de sistem necesare pentru pdfplumber și matplotlib
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiem fișierul de dependențe și instalăm pachetele Python
# Facem asta înainte de a copia codul sursă pentru a profita de cache-ul Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiem tot codul sursă în container
COPY . .

# Expunem portul pe care rulează Streamlit
EXPOSE 8501

# Streamlit are nevoie de aceste variabile pentru a rula în container fără browser
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Comanda de pornire a aplicației
CMD ["python", "-m", "streamlit", "run", "src/app.py"]