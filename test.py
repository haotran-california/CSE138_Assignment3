import requests

url = 'http://10.0.0.242:8090/view'
data = {'socket_address': '1234.1234.1234.1234'}

response = requests.put(url, json=data)
print(response)
print(response.text)

response = requests.put('http://1234.1234.1234.1234', json=data)
print(response)
print(response.text)

'''response = requests.request('CUSTOM', url, json=data)
print(response)

response = requests.get(url)
print(response)'''

# Figure out how to verify that initSelf and sendInit are working