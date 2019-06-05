import os
import json
import urllib.request
import decimal

from bitcoinrpc.authproxy import AuthServiceProxy
from flask import Flask, request, render_template

app = Flask(__name__)
conn = None
RPC_URI = os.environ['RPC_URI']
ASSET_DETAILS_API = os.environ['ASSET_DETAILS_API']


def read_asset_details():
    asset_details = {}
    try:
        asset_details = json.loads(urllib.request.urlopen(ASSET_DETAILS_API).read()
                                   .decode('utf-8'))
    except Exception:
        pass
    return asset_details


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def get_rpc_connection():
    return AuthServiceProxy(RPC_URI)


@app.route("/", methods=['GET'])
def wallet_info():
    asset_details = read_asset_details()
    try:
        rpc_connection = get_rpc_connection()
        info = rpc_connection.getwalletinfo()
        address = rpc_connection.getnewaddress()
        for key, value in info["balance"].items():
            if not asset_details.get(key):
                asset_details[key] = {"name": "", "image_url": ""}
            if key == "bitcoin":
                asset_details[key]['name'] = 'bitcoin'
                asset_details[key]['image_url'] = 'https://bitcoin.org/img/icons/opengraph.png'
    except Exception:
        info = {}
        address = ''
    return render_template('wallet_info.html', wallet_info=info, address=address, asset_details=asset_details)


@app.route("/transactions/", methods=['GET'])
def transactions():
    try:
        rpc_connection = get_rpc_connection()
        info = rpc_connection.listtransactions()
    except Exception:
        info = {}
    return render_template('transactions.html', transactions=info)


@app.route("/send_asset/", methods=['GET'])
def send_asset():
    return render_template('send_asset.html')


@app.route("/api/v1/get_transactions/", methods=['GET'])
def get_transactions_api():
    try:
        rpc_connection = get_rpc_connection()
        response = rpc_connection.listtransactions()
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response, cls=DecimalEncoder),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(response, cls=DecimalEncoder),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/get_wallet_info/", methods=['GET'])
def get_wallet_info_api():
    try:
        rpc_connection = get_rpc_connection()
        response = rpc_connection.getwalletinfo()
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response, cls=DecimalEncoder),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(response, cls=DecimalEncoder),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/get_address/", methods=['GET'])
def get_address_api():
    try:
        rpc_connection = get_rpc_connection()
        address = rpc_connection.getnewaddress()
        response = {"address": address}
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response, cls=DecimalEncoder),
            status=500,
            mimetype='application/json'
        )
    return app.response_class(
        response=json.dumps(response, cls=DecimalEncoder),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/send_asset/", methods=['POST'])
def send_asset_api():
    try:
        rpc_connection = get_rpc_connection()
        data = request.json
        address = data['address']
        asset_amount = data['asset_amount']
        asset_identifier = data['asset_identifier']
        comment = ''
        comment_to = ''
        subtract_fee_from_amount = False
        replaceable = False
        conf_target = 1
        estimate_mode = "UNSET"

        txn_id = rpc_connection.sendtoaddress(address, asset_amount, comment, comment_to,
                                              subtract_fee_from_amount, replaceable, conf_target,  estimate_mode,
                                              asset_identifier)
        rpc_connection.generate(1)
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response, cls=DecimalEncoder),
            status=500,
            mimetype='application/json'
        )
    response = {"txn_id": txn_id}
    return app.response_class(
        response=json.dumps(response, cls=DecimalEncoder),
        status=200,
        mimetype='application/json'
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
