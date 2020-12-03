FROM python:3.10.4

ENV PORT 5000
ENV APP_HOME /app

WORKDIR $APP_HOME
COPY . .

RUN pip install -r requirements.txt

EXPOSE $PORT

CMD python3 app.py
