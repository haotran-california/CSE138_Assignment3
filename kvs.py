from flask import Flask, request, jsonify
import requests
import os 
import time

SOCKET_ADDR = os.getenv("SOCKET_ADDRESS")
FORWARDING_ADDRESS = os.getenv("FORWARDING_ADDRESS")
FORWARD_URL = ""
app = Flask(__name__)

#FIELDS
uniqueID = None
dict = {}
peers = []
vectorClock = []
nextUniqueID = None


#FORWARDING FUNCTIONS
def forwardingGET(key): 
  try: 
    res = requests.get(FORWARD_URL + "/" + key, timeout=3)
    content = res.json()
    status_code = res.status_code

    if status_code == 200 or status_code == 404: 
      return jsonify(content), status_code
    else: 
      return jsonify({"error": "Cannot forward request"}), 503
  except: 
    return jsonify({"error": "Cannot forward request"}), 503

#assume key() grabs the value from the body 
def forwardingPUT(key, value): 
  payload = {
    "value": value
  }
  try: 
    res = requests.put(FORWARD_URL + "/" + key, json=payload, timeout=3)
    content = res.json()
    status_code = res.status_code

    if status_code == 200 or status_code == 201 or status_code == 400: 
      return jsonify(content), status_code
    else: 
      return jsonify({"error": "Cannot forward request"}), 503
  except:  
    return jsonify({"error": "Cannot forward request"}), 503


def forwardingDELETE(key): 
  try: 
    res = requests.delete(FORWARD_URL + "/" + key, timeout=3)
    content = res.json()
    status_code = res.status_code

    if status_code == 200 or status_code == 404: 
      return jsonify(content), status_code
    else: 
      return jsonify({"error": "Cannot forward request"}), 503
  except:
    return jsonify({"error": "Cannot forward request"}), 503

#--------------------------------------------------------------

def mainGET(key): 
  if key in dict:
    val = dict[key]
    return jsonify({"result": "found", "value": val}), 200
  else:
    return jsonify({"error": "Key does not exist"}), 404
    

def mainPUT(key, value): 
    if not value: 
      return jsonify({"error": "PUT request does not specify a value"}), 400
    if len(key) > 50:
      return jsonify({"error": "Key is too long"}), 400
    elif key in dict:
      dict[key] = value 
      return jsonify({"result": "replaced"}), 200
    else:
      dict[key] = value
      return jsonify({"result": "created"}), 201

def mainDELETE(key): 
  if key in dict:
    del dict[key]
    return jsonify({"result": "deleted"}), 200
  else:
    return jsonify({"error": "Key does not exist"}), 404


#----------------------------------------------------

#VIEW FUNCTIONS
def addReplica(socketAddress, senderIP): 
  if socketAddress in peers:
    return jsonify({"result": "already present"}, 200)

  peers.append(socketAddress)
  vectorClock.append(0)
  retry = []

  if senderIP not in peers: 
    uniqueID = nextUniqueID
    vectorClock[uniqueID] += 1 

    for replicaIP in peers: 
      retry = []
      URL = "http:" + replicaIP + "/" + socketAddress 
      try: 
        resp = request.put(URL)
        status_code = resp.status_code
        if status_code == 503: 
          retry.append(replicaIP)
      except: 
        continue

  while(retry): 
    time.sleep(1)
    for replicaIP in retry: 
      URL = "http:" + replicaIP + "/" + socketAddress
      try: 
        resp = request.put(URL)
        status_code = resp.status_code
        if status_code == 200 or status_code == 201: 
          retry.remove(replicaIP)
      except: 
        continue
      
  nextUniqueID += 1 


def deleteReplica(socketAddress, senderIP): 
  if socketAddress == SOCKET_ADDR: 
    peers = []
    vectorClock = []
    return jsonify({"result": "deleted"}, 200)
  if socketAddress not in peers: 
    return jsonify({"error": "view has no such replica"}, 404)
  if senderIP not in peers: 
    for replicaIP in peers: 
      URL = "http://" + replicaIP + "/" + socketAddress
      try: 
        res = requests.delete(URL, timeout=3)
      except: 
        continue 
  return jsonify({}, 200)

def getReplicas(): 
  return jsonify({"view": peers}, 200)

handleGET, handlePUT, handleDELETE = None, None, None 
instanceIP = None

if FORWARDING_ADDRESS: 
  handleGET = forwardingGET
  handlePUT = forwardingPUT
  handleDELETE = forwardingDELETE
  FORWARD_URL = "http://" + FORWARDING_ADDRESS + "/kvs"
else: 
  handleGET = mainGET
  handlePUT = mainPUT
  handleDELETE = mainDELETE

@app.route('/kvs/<key>', methods=['GET', 'PUT', 'DELETE'])
def key(key):
  if request.method == 'GET':
    return handleGET(key)
  elif request.method == 'PUT':
    value = None
    data = request.get_json()
    if data: 
      value = data['value']
    return handlePUT(key, value)
  elif request.method == 'DELETE':
    return handleDELETE(key)
  else: 
    return "Method Not Allowed", 405

@app.route('/view/<ip>', methods=['GET', 'PUT', 'DELETE'])
def key2(ip): 
  senderIP = request.remote_addr
  if request.method == 'GET': 
    return getReplicas()
  if request.method == 'PUT': 
    return addReplica(ip, senderIP)
  if request.method == 'DELETE': 
    return deleteReplica(ip, senderIP)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090)