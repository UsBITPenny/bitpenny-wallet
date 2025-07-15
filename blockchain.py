import hashlib
import json
import os
from time import time
from flask import Flask, jsonify, request, send_file

# === CONFIG ===
COIN_NAME = "BIT-Penny"
TICKER = "BITP"
MAX_SUPPLY = 1_000_000_000_000
REWARD_AMOUNT = 800_000_000
MY_WALLET = "156HhnAdchmSKHV9GdjP32wMau4cWGyPXg"

# === BLOCKCHAIN ===
class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.total_issued = 0
        self.new_block(previous_hash='1', proof=100)

    def new_block(self, proof, previous_hash=None):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })
        return self.last_block['index'] + 1

    def get_balance(self, address):
        balance = 0
        for block in self.chain:
            for tx in block['transactions']:
                if tx['recipient'] == address:
                    balance += tx['amount']
                if tx['sender'] == address:
                    balance -= tx['amount']
        return balance

    def circulating_supply(self):
        supply = 0
        for block in self.chain:
            for tx in block['transactions']:
                if tx['sender'] == "COINBASE":
                    supply += tx['amount']
        return supply

    def can_mine(self):
        return self.circulating_supply() + REWARD_AMOUNT <= MAX_SUPPLY

    def hash(self, block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

# === LOAD BLOCKCHAIN ===
blockchain = Blockchain()
if os.path.exists("blockchain.json"):
    with open("blockchain.json", "r") as f:
        blockchain.chain = json.load(f)

# === FLASK SERVER ===
app = Flask(__name__)

@app.route('/')
def wallet_ui():
    return send_file("wallet.html")

@app.route('/mine', methods=['GET'])
def mine():
    if not blockchain.can_mine():
        return jsonify({"message": "💸 Max coin supply reached. No more mining allowed."}), 400

    last_proof = blockchain.last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    blockchain.new_transaction(sender="COINBASE", recipient=MY_WALLET, amount=REWARD_AMOUNT)
    previous_hash = blockchain.hash(blockchain.last_block)
    block = blockchain.new_block(proof, previous_hash)

    # Save to file
    with open("blockchain.json", "w") as f:
        json.dump(blockchain.chain, f, indent=4)

    return jsonify(block), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    data = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in data for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(data['sender'], data['recipient'], data['amount'])
    return jsonify({'message': f'Transaction will be added to Block {index}'}), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    return jsonify({'chain': blockchain.chain, 'length': len(blockchain.chain)}), 200

@app.route('/balance/<address>', methods=['GET'])
def get_balance(address):
    balance = blockchain.get_balance(address)
    return jsonify({'address': address, 'balance': balance}), 200

@app.route('/supply', methods=['GET'])
def supply():
    return jsonify({
        "ticker": TICKER,
        "name": COIN_NAME,
        "supply": blockchain.circulating_supply(),
        "max": MAX_SUPPLY
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
