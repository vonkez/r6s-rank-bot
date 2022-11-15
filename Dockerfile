FROM python:3.10-alpine
COPY . .
RUN pip install -r ./requirements.txt
RUN sudo apt-get install gcc
CMD [“python”, “./main.py”] 
