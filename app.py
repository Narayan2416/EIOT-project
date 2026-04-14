from flask import Flask, request, jsonify

app = Flask(__name__)

lis=[]


@app.route('/data', methods=['GET', 'POST'])
def receive_data():
    if request.method == 'POST':
        data = request.json
        print("Received:", data)
        lis.append(data)
        return jsonify({"status": "success"})
    
    else:
        return jsonify(lis)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)