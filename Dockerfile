FROM python
RUN pip install flask
RUN pip install requests
RUN pip install colorama
ADD main.py ./
CMD ["python3", "main.py"]
