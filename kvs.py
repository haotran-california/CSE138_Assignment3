from flask import Flask, request, jsonify
import os
import requests
from time import sleep
import json
from typing import Dict, Any
from colorama import Fore, Back, Style

app = Flask(__name__)
kvs = dict()
peers = []
vectorClock = [0]
uniqueID = 0
nextUID = 1

green = Fore.GREEN
blue = Fore.BLUE
red = Fore.RED
white = Fore.WHITE

############### VIEW ##############

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
  peers = json.loads(payload.get('peers'))
  peers.append('http://' + request.remote_addr + ':8090/')
  print(green + 'Replica finished INITPACKAGE' + white)
  return jsonify({"result": "success"}), 200

"""Returns jsonified peers"""
@app.route('/view', methods=['GET'])
def getView():
  print(green + 'Replica did getView()')
  return jsonify({"view": peers}), 200

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
      'peers': str(peers),
    }
    response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
    while response.status_code != 200:
      print("NO RESPONSE REPLY AFTER INITPACKAGE RECEIVED")
      sleep(1)
      response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
    
    for peer in peers:
      response = requests.put(peer, json={'socket-address': newReplicaIP})
      if response.status_code not in [200, 201]:
        retry.append(peer)
      
    while retry:
      print(red + "FAILED TO GET REPLY AFTER RETRY" + white)
      newRetry = []
      for peer in retry:
        response = requests.put(peer, newReplicaIP)
        if response.status_code not in [200, 201]:
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
        if response.status_code not in [200, 201]:
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

  causalMetadata  = payload.get('causal-metadata')

  # if causalMetadata is not null:
  if type(causalMetadata) != type(None):
    print("causal metadata is not null")
    # Load causalMetadata as a list
    causalMetadata = json.loads(causalMetadata)

    if vectorClock[uniqueID] < causalMetadata[uniqueID]:
      print(red + 'Replica finished putKvs with 503' + white)
      return jsonify({"error": "causal dependencies not satisfied; try again later"}), 503
  else:
    print("causal metadata is null")
    causalMetadata = [0] * len(vectorClock)

  resultCode = 503
  if key not in kvs:
    resultCode = 201
  else:
    resultCode = 200

  kvs[key] = value
  print(vectorClock)
  print(uniqueID)
  vectorClock[uniqueID] += 1
  vectorClock = maxOutClock(vectorClock, causalMetadata)

  if senderIP not in peers:
    retry = []
    data = {
      'value': value,
      'causal-metadata': json.dumps(vectorClock),
    }

    for peer in peers:
      print("PEER:", peer)
      response = requests.put(peer + 'kvs/' + key, json=data)
      if response.status_code == 503:
        retry.append(peer)
      elif response.status_code in [200, 201]:
        responsePayload = response.json()
        responseCM = json.loads(responsePayload['causal-metadata'])
        vectorClock = maxOutClock(vectorClock, responseCM)
        
    while retry:
      newRetry = []
      data = {
        'value': value,
        'causal-metadata': json.dumps(vectorClock) 
      }
      for peer in retry:
        response = requests.put(peer + 'kvs/' + key, json=data)
        responsePayload = response.json()
        responseCM = json.loads(responsePayload['causal-metadata'])
        if response.status_code not in [200, 201]:
          newRetry.append(peer)
          vectorClock = maxOutClock(vectorClock, responseCM)
      retry = newRetry

  if resultCode == 200:
    print(green + 'Replica finished putKvs() with 200' + white)
    return jsonify({'result': 'replaced', 'causal-metadata': json.dumps(vectorClock)}), 200
  elif resultCode == 201:
    print(green + 'Replica finished putKvs() with 201' + white)
    return jsonify({'result': 'created', 'causal-metadata': json.dumps(vectorClock)}), 201

@app.route('/kvs/<key>', methods=['GET'])
def getKvs(key: str):
  print(blue + 'Replica starting getKvs()...' + white)
  
  senderIP = 'http://' + request.remote_addr + ':8090/'
  payload = request.get_json()
  causalMetadata = payload.get('causal-metadata')
  if type(causalMetadata) != type(None):
    print("causal metadata is not none")
    causalMetadata = json.loads(causalMetadata)

    if vectorClock[uniqueID] < causalMetadata[uniqueID]:
      print(red + 'Replica finished getKvs with 503' + white)
      return jsonify({"error": "causal dependencies not satisfied; try again later"}), 503
  
  if key not in kvs:
    print(red + 'Replica finished getKvs with 404' + white)
    return jsonify({"error": "Key does not exist"}), 404

  vectorClock[uniqueID] += 1

  print(green + 'Replica finished getKvs with 200')
  return jsonify({"result": "found", "value": kvs[key], 'causal-metadata': json.dumps(vectorClock)})

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8090)