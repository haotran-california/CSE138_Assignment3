from flask import jsonify
import requests

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