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
vectorClock = []
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
    'vectorClock': str(vectorClock),
    'keyStore': json.dumps(keyStore),
  }

  #response = requests.request('INITPACKAGE', newReplicaIP, json=jsonify(payload))
  # temporarily make newReplicaIP self ip for testing
  response = requests.request('INITPACKAGE', 'http://10.0.0.242:8090', json=payload)
  
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
  vectorClock = payload.get('vectorClock')
  kvs = json.loads(payload.get('keyStore'))
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
  return jsonify({"view:": peers}), 200

@app.route('/view', methods=['PUT'])
def putView():
  global kvs, nextUID, vectorClock
  
  senderIP = request.remote_addr
  payload = request.get_json()
  newReplicaIP = payload.get('socket_address')

  if newReplicaIP in peers:
    return jsonify({"result": "already present"}), 200
  
  peers.append(newReplicaIP)
  vectorClock.append(0)
  retry = []

  if senderIP not in peers:
    # Send initialization package to replica
    #sendInit(senderIP, uniqueID, nextUID, vectorClock, kvs)
    # for now make senderIP itself
    sendInit(newReplicaIP, nextUID, vectorClock, kvs)


  print(f"Added peer: {newReplicaIP}")
  print("Current peers:", peers)
  return jsonify({"message": "Peer added successfully"}), 200

@app.route('/view', methods=['DELETE'])
def deleteView():
  return

def view():
  print("In view")
  client_ip = request.remote_addr
  method = request.method
  print("method:", method, "client_ip:", client_ip)

  # Returns the list of peers
  if method == 'GET':
    return jsonify(peers), 200

  # Puts a replica into the system
  elif method == 'PUT':
    try:
      data = request.get_json()
      socket_address = data.get('socket_address')

      if not socket_address:
        raise ValueError("Invalid data: 'socket_address' missing")
            
      return putView(socket_address, client_ip)

    except Exception as e:
      print(f"Error: {str(e)}")
      return jsonify({"error": str(e)}), 400

  elif method == 'DELETE':
    print('Request is DELETE')

  else:
    print('UNKNOWN METHOD')
    
  return jsonify({"Hello": "from view!"}), 200
############### KVS ##############
#@app.route('/kvs/<key>', methods=['GET', 'PUT', 'DELETE', 'CUSTOM'])
#def kvs(key):
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
  
  return jsonify({"Hello": "from kvs with key " + str(key)}), 200

if __name__ == "__main__":
  app.run(host='0.0.0.0', port=8090)