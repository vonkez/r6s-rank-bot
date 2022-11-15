FROM python:3.10-alpine
COPY . .
RUN apk add gcc
RUN pip install -r ./requirements.txt
CMD [“python”, “./main.py”] 
