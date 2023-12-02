import requests
import json
from flask import jsonify

url = 'http://10.0.0.242:8090/view'
data = {'socket-address': 'http://10.0.0.242:8090/'}

print("Attempting put of", url)
response = requests.put(url, json=data)
print(response)
print(response.text)

response = requests.get(url)
print(response)
print(response.text)

print("Attempting delete of", data.get('socket-address'))
response = requests.delete(url, json={'socket-address': 'http://10.0.0.242:8090/'})
print(response)
print(response.text)

print("Starting kvs tests")
url = 'http://10.0.0.242:8090/kvs/'
cm = None

keys = ['apple', 'banana', 'pear']
values = ['zero', 'one', 'two']

data = {'casual-metadata': cm}
print("data: ", data)

for i, key in enumerate(keys):
  data = {'casual-metadata': cm, 'value': i}
  response = requests.put(url + key, json=data)
  print(response)
  print(response.text)
  payload = response.json()

'''response = requests.put('http://1234.1234.1234.1234', json=data)
print(response)
print(response.text)'''

'''response = requests.request('CUSTOM', url, json=data)
print(response)

response = requests.get(url)
print(response)'''

# Figure out how to verify that initSelf and sendInit are working