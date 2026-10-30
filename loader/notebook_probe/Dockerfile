# The client side of the upload notebook: Python with pyodbc, the Microsoft ODBC driver and a
# Jupyter kernel, as a HIC analyst's machine has them. Built by loader/notebook_probe.sh.
FROM python:3.12-slim-trixie
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates unixodbc \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
 && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir pandas==2.2.3 pyodbc==5.1.0 nbclient==0.10.0 nbformat==5.10.4 ipykernel==6.29.5 \
 && python -m ipykernel install --name python3
WORKDIR /work
CMD ["python3"]
