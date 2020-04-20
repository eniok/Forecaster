FROM python:3.7
WORKDIR /Forecaster
COPY . /Forecaster
RUN pip install -U -r requirements.txt
EXPOSE 8080
CMD ["python" , "app.py"]
