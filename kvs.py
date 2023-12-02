from flask import Flask, request, jsonify
import os
import requests
from time import sleep
import json
from typing import Dict, Any
from colorama import Fore, Back, Style

FORWARDING_ADDRESS = os.getenv("FORWARDING_ADDRESS")
FORWARD_URL = ""
app = Flask(__name__)
kvs = dict(test1=2, test2=3)
peers = []
vectorClock = [0]
uniqueID = 0
nextUID = 0

green = Fore.GREEN
blue = Fore.BLUE
red = Fore.RED
white = Fore.WHITE

############### VIEW ##############
"""
Sends the following fields to a ip with the method 'INITPACKAGE':
  senderIP: str
  uniqueID: str
  nextUniqueID: str
  vectorClocK: [int]
  kvs: dict
"""
def sendInit(newReplicaIP: str, nextUniqueId: int, vectorClock: [int], keyStore):
  print(blue + 'Replica doing sendInit...' + white)
  print('serialize:', json.dumps(keyStore))
  payload = {
    'uniqueID': str(nextUniqueId),
    'nextUniqueID': str(nextUniqueId + 1),
    'vectorClock': json.dumps(vectorClock),
    'keyStore': json.dumps(keyStore),
  }

  response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
  # temporarily make newReplicaIP self ip for testing
  #response = requests.request('INITPACKAGE', 'http://10.0.0.242:8090/', json=payload)
  
  while response.status_code not in [200, 201]:
    response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
    sleep(1)

  print(green + 'Replica finished sendInit\n' + white)
  return

"""
Received the method INITPACKAGE and sets current fields to received values
"""
@app.route('/', methods=['INITPACKAGE'])
def initSelf():
  print(blue + 'Replica doing INITPACKAGE...' + white)
  global uniqueID, nextUID, vectorClock, kvs
  payload = request.get_json()
  uniqueID = int(payload.get('uniqueID'))
  nextUID = int(payload.get('nextUniqueID'))
  vectorClock = json.loads(payload.get('vectorClock'))
  kvs = json.loads(payload.get('keyStore'))
  peers.append('http://' + request.remote_addr + ':8090/')
  print(green + 'Replica finished INITPACKAGE' + white)
  return jsonify({"result": "success"}), 200

"""
Helper function that prints out global variables
"""
def checkglobals():
  global uniqueID, nextUID, vectorClock, kvs
  print(blue + "Starting globals check" + white)
  print("uniqueID:", uniqueID)
  print("nextUID:", nextUID)
  print("vectorClock:", vectorClock)
  print("kvs:", kvs)
  print(blue + "Globals check finished" + white)

"""Returns jsonified peers"""
@app.route('/view', methods=['GET'])
def getView():
  print(green + 'Replica did getView()')
  return jsonify({"view:": peers}), 200

@app.route('/view', methods=['PUT'])
def putView():
  print(blue + "Replica received starting putView()" + white)

  global kvs, nextUID, vectorClock
  
  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  newReplicaIP = payload.get('socket-address')

  if newReplicaIP in peers:
    print(green + 'Replica finished putView() with 200' + white)
    return jsonify({"result": "already present"}), 200

  vectorClock.append(0)

  if senderIP not in peers:
    retry = []
    # Send initialization package to replica
    payload = {
      'uniqueID': str(nextUID),
      'nextUniqueID': str(nextUID + 1),
      'vectorClock': str(vectorClock),
      'keyStore': json.dumps(kvs),
    }
    response = requests.request('INITPACKAGE', newReplicaIP, json=payload)
    while response.status_code != 200:
      print("NO RESPONSE REPLY AFTER INITPACKAGE RECEIVED")
      sleep(1)
      response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
    
    for peer in peers:
      response = requests.put(peer, json={'socket-address': senderIP})
      if response.status_code not in [200, 201]:
        retry.append(peer)
      
    while retry:
      print(red + "FAILED TO GET REPLY AFTER RETRY" + white)
      newRetry = []
      for peer in retry:
        response = requests.put(peer, newReplicaIP)
        if response.status_code in [200, 201]:
          newRetry.append(peer)
      retry = newRetry
      sleep(1)
  
  peers.append(newReplicaIP)

  print(f"Added peer: {newReplicaIP}")
  print("Current peers:", peers)
  print(green + 'Replica finished putView with 201' + white)
  return jsonify({"message": "Peer added successfully"}), 201

@app.route('/view', methods=['DELETE'])
def deleteView():
  print(blue + 'Replica starting deleteView()' + white)
  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  targetReplicaIP = payload.get('socket-address')

  selfIP = request.url_root
  if targetReplicaIP == selfIP:
    print("Received order to remove self")
    global peers, vectorClock, uniqueID, nextUID, kvs
    peers = []
    vectorClock = [0]
    uniqueID = 0
    nextUID = 1
    kvs = dict()
    print(green + 'Replica finished deleteView by removing self with code 200' + white)
    return jsonify({"message": "Removed self"}), 200
  
  if targetReplicaIP not in peers:
    print(type(targetReplicaIP))
    print(peers)
    print(red + 'Replica finished deleteView with 404' + white)
    return jsonify({"error": "View has no such replica"}), 404
  
  if senderIP not in peers:
    retry = []
    for peer in peers:
      response = requests.delete(peer, json=targetReplicaIP)
      if response.status_code != 200:
        retry.append(peer)

    while retry:
      newRetry = []
      for peer in retry:
        response = requests.delete(peer, json=targetReplicaIP)
        if response.status_code != 200:
          newRetry.append(peer)
      newRetry = retry
      sleep(1)

  peers.remove(targetReplicaIP)

  print(green + 'Replica finished deleteView with code 200' + white)
  return jsonify({"result": "deleted"}), 200

############### KVS ##############
def maxOutClock(vectorClockA, vectorClockB):
  if len(vectorClockA) < len(vectorClockB):
    vectorClockA += [0] * (len(vectorClockB) - len(vectorClockA))
  elif len(vectorClockB) < len(vectorClockA):
    vectorClockB += [0] * len(vectorClockB)
  return max(vectorClockA, vectorClockB)

@app.route('/kvs/<key>', methods=['PUT'])
def putKvs(key: str):
  print(blue + 'Replica starting putKvs()...' + white)
  global vectorClock

  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  value = str(payload.get('value'))

  if not value:
    print(red + 'Replica finished putKvs with 400' + white)
    return jsonify({"error": "PUT request does not specify a value"}), 400
  if len(value) > 100:
    print(red + 'Replica finished putKvs with 400' + white)
    return jsonify({"error": "Key is too long"}), 400

  casualMetadata  = payload.get('casual-metadata')
  print("Sender ip:", senderIP)
  print("Casual metadata:", casualMetadata)
  print("key:", key)

  # if casualMetadata is not null:
  if type(casualMetadata) != type(None):
    print("Casual metadata is not null")
    # Load casualMetadata as a list
    casualMetadata = json.loads(casualMetadata)
    casualMetadata = [1, 2, 3, 4, 5, 6, 7]

    if vectorClock[uniqueID] < casualMetadata[uniqueID]:
      print(red + 'Replica finished putKvs with 503' + white)
      return jsonify({"error": "Casual dependencies not satisfied; try again later"}), 503
  else:
    print("Casual metadata is null")
    casualMetadata = [0] * len(vectorClock)

  resultCode = 503
  if key not in kvs:
    resultCode = 201
  else:
    resultCode = 200

  kvs[key] = value
  print(vectorClock)
  print(uniqueID)
  vectorClock[uniqueID] += 1
  vectorClock = maxOutClock(vectorClock, casualMetadata)

  if senderIP not in peers:
    retry = []
    data = {
      'value': value,
      'casual-metadata': json.dumps(vectorClock),
    }

    for peer in peers:
      print("PEER:", peer)
      response = requests.put(peer + 'kvs/' + key, json=data)
      if response.status_code == 503:
        retry.append(peer)
      elif response.status_code in [200, 201]:
        responsePayload = response.json()
        responseCM = json.loads(responsePayload['casual-metadata'])
        vectorClock = maxOutClock(vectorClock, responseCM)
        
    while retry:
      newRetry = []
      data = {
        'value': value,
        'casual-metadata': json.dumps(vectorClock) 
      }
      for peer in retry:
        response = requests.put(peer + 'kvs/' + key, json=data)
        responsePayload = response.json()
        responseCM = json.loads(responsePayload['casual-metadata'])
        if response.status_code not in [200, 201]:
          newRetry.append(peer)
          vectorClock = maxOutClock(vectorClock, responseCM)
      retry = newRetry

  if resultCode == 200:
    print(green + 'Replica finished putKvs() with 200' + white)
    return jsonify({'result': 'created', 'casual-metadata': json.dumps(vectorClock)}), 200
  elif resultCode == 201:
    print(green + 'Replica finished putKvs() with 201' + white)
    return jsonify({'result': 'replaced', 'casual-metadata': json.dumps(vectorClock)}), 201

#@app.route('/kvs/<key>', methods=['GET', 'PUT', 'DELETE', 'CUSTOM'])
'''def kvs(key):"
  print("in kvs")
  client_ip = request.remote_addr
  method = request.method
  if method == 'GET':
    print('Request is GET')
  elif method == 'PUT':
    print('Request is PUT')
  elif method == 'DELETE':
    print('Request is DELETE')
  elif method == 'CUSTOM':
    print('CUSTOM METHOD INVOKED')
  else:
    print('UNKNOWN METHOD')
  
  return jsonify({"Hello": "from kvs with key " + str(key)}), 200'''

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8090)