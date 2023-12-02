from flask import Flask, request, jsonify
import os
import requests
from time import sleep
import json
from typing import Dict, Any

FORWARDING_ADDRESS = os.getenv("FORWARDING_ADDRESS")
FORWARD_URL = ""
app = Flask(__name__)
kvs = dict(test1=2, test2=3)
peers = []
vectorClock = [0]
uniqueID = 0
nextUID = 0

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
  print("in sendInit")
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

  return

"""
Received the method INITPACKAGE and sets current fields to received values
"""
@app.route('/', methods=['INITPACKAGE'])
def initSelf():
  global uniqueID, nextUID, vectorClock, kvs
  checkglobals()
  payload = request.get_json()
  uniqueID = payload.get('uniqueID')
  nextUID = payload.get('nextUniqueID')
  vectorClock = json.loads(payload.get('vectorClock'))
  kvs = json.loads(payload.get('keyStore'))
  peers.append('http://' + request.remote_addr + ':8090/')
  checkglobals()
  return jsonify({"result": "success"}), 200

"""
Helper function that prints out global variables
"""
def checkglobals():
  global uniqueID, nextUID, vectorClock, kvs
  print("Starting globals check")
  print("uniqueID:", uniqueID)
  print("nextUID:", nextUID)
  print("vectorClock:", vectorClock)
  print("kvs:", kvs)
  print("Globals check finished")

"""Returns jsonified peers"""
@app.route('/view', methods=['GET'])
def getView():
  print("SELF IP:", request.url_root)
  return jsonify({"view:": peers}), 200

@app.route('/view', methods=['PUT'])
def putView():
  global kvs, nextUID, vectorClock
  
  senderIP = 'http://' + request.remote_addr + ':8090/'
  print("SENDERIP:", senderIP)
  payload = request.get_json()
  newReplicaIP = payload.get('socket-address')

  if newReplicaIP in peers:
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
      print("SENDER IP:", senderIP)
      response = requests.put(peer, json={'socket-address': senderIP})
      if response.status_code not in [200, 201]:
        retry.append(peer)
      
    while retry:
      print("FAILED TO GET REPLY AFTER RETRY", retry)
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
  return jsonify({"message": "Peer added successfully"}), 200

@app.route('/view', methods=['DELETE'])
def deleteView():
  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  targetReplicaIP = payload.get('socket-address')

  selfIP = request.url_root
  if targetReplicaIP == selfIP:
    print("Received order to remove self")
    global peers, vectorClock, uniqueID, nextUID, kvs
    peers = []
    vectorClock = []
    uniqueID = 0
    nextUID = 1
    kvs = dict()
    return jsonify({"message": "Removed self"}), 200
  
  if targetReplicaIP not in peers:
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

  return jsonify({"result": "deleted"}), 200

############### KVS ##############
@app.route('/kvs/<key>', methods=['PUT'])
def putKvs(key):
  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  key = payload.get('value')
  casualMetadata  = payload.get('casual-metadata')
  print("Sender ip:", senderIP)
  print("Casual metadata:", casualMetadata)
  print("key:", key)

  if type(casualMetadata) != type(None):
    print("casualMetadata is not None")

    casualMetadata = json.loads(casualMetadata)
    print("casualMetadata:", casualMetadata)
    print("casualMetadata type:", type(casualMetadata))
    print(vectorClock[uniqueID])
    print(casualMetadata[uniqueID])
    if vectorClock[uniqueID] < casualMetadata[uniqueID]:
      return jsonify({"error": "Casual dependencies not satisfied; try again later"}), 503
    print("It is of type:", type(casualMetadata))
    print(casualMetadata)

  return jsonify({'temp key': key}), 200
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