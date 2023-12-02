FROM python
RUN pip install flask
RUN pip install requests
RUN pip install colorama
ADD kvs.py ./
CMD ["python3", "kvs.py"]
