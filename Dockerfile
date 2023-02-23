FROM python:3.6
WORKDIR /app
COPY . /app

RUN apt-get update && apt-get install -y libpq-dev libssl-dev libffi-dev

RUN pip install -r requirements.txt
RUN #python manage.py loaddata crm lessons products teachers