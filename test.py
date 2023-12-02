import requests

url = 'http://10.0.0.242:8090/view'
data = {'socket_address': 'http://10.0.0.242:8090'}

print("Attempting put of", url)
response = requests.put(url, json=data)
print(response)
print(response.text)

response = requests.get(url)
print(response)
print(response.text)

print("Attempting delete of", url)
response = requests.delete(url, json={'socket_address': 'http://10.0.0.242:8090'})
print(response)
print(response.text)

'''response = requests.put('http://1234.1234.1234.1234', json=data)
print(response)
print(response.text)'''

'''response = requests.request('CUSTOM', url, json=data)
print(response)

response = requests.get(url)
print(response)'''

# Figure out how to verify that initSelf and sendInit are working