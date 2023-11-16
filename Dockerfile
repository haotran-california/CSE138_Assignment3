FROM python
RUN pip install flask
RUN pip install requests
ADD kvs.py /
CMD ["python3", "./kvs.py"]
