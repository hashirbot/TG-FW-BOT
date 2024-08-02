FROM python:3.11

WORKDIR /TG-FW-BOT

COPY . /TG-FW-BOT

RUN pip install -r requirements.txt

CMD ["python", "bot.py"]
