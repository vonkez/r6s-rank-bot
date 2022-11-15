FROM python:3.10-alpine
COPY . .
RUN apt-get install gcc
RUN pip install -r ./requirements.txt
CMD [“python”, “./main.py”] 
