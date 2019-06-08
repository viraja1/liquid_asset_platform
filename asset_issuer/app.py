import os
import json
import decimal
import sqlite3

from bitcoinrpc.authproxy import AuthServiceProxy
from flask import Flask, request, render_template

app = Flask(__name__)
conn = None
RPC_URI = os.environ['RPC_URI']


def get_db_connection():
    db_file = "./assets.db"
    global conn
    if conn is None:
        conn = sqlite3.connect(db_file, check_same_thread=False)
        create_table()
    return conn


def create_table():
    try:
        connection = get_db_connection()
        c = connection.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS Asset (asset_id, asset_name, asset_image_url)""")
        connection.commit()
    except Exception:
        pass


def create_asset_entry(asset_id, asset_name, asset_image_url):
    connection = get_db_connection()
    c = connection.cursor()
    c.execute("""INSERT INTO Asset (asset_id, asset_name, asset_image_url) values(?, ?, ?)""",
              (asset_id, asset_name, asset_image_url))
    connection.commit()


def read_asset_details():
    connection = get_db_connection()
    c = connection.cursor()
    results = c.execute("""Select * from Asset""").fetchall()
    asset_details = {}
    for result in results:
        asset_details[result[0]] = {"name": result[1], "image_url": result[2]}
    return asset_details


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)


def get_rpc_connection():
    return AuthServiceProxy(RPC_URI)


@app.route("/", methods=['GET'])
def home():
    asset_details = read_asset_details()
    try:
        rpc_connection = get_rpc_connection()
        assets = rpc_connection.listissuances()
    except Exception:
        assets = []
    final_assets = []
    for asset in assets:
        if asset_details.get(asset['asset']):
            asset['name'] = asset_details[asset['asset']]['name']
            asset['image_url'] = asset_details[asset['asset']]['image_url']
        else:
            asset['name'] = ''
            asset['image_url'] = ''
        if asset.get('assetlabel') == 'bitcoin':
            continue
        final_assets.append(asset)
    return render_template('index.html', assets=final_assets)


@app.route("/wallet_info/", methods=['GET'])
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
        info = rpc_connection.listtransactions("*", 100000)
    except Exception:
        info = {}
    return render_template('transactions.html', transactions=info)


@app.route("/issue_asset/", methods=['GET'])
def issue_asset():
    return render_template('issue_asset.html')


@app.route("/send_asset/", methods=['GET'])
def send_asset():
    return render_template('send_asset.html')


@app.route("/api/v1/get_transactions/", methods=['GET'])
def get_transactions_api():
    try:
        rpc_connection = get_rpc_connection()
        response = rpc_connection.listtransactions("*", 100000)
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


@app.route("/api/v1/get_issued_assets/", methods=['GET'])
def get_issued_assets_api():
    try:
        rpc_connection = get_rpc_connection()
        assets = rpc_connection.listissuances()
    except Exception as e:
        response = {"error": str(e)}
        return app.response_class(
            response=json.dumps(response, cls=DecimalEncoder),
            status=500,
            mimetype='application/json'
        )

    return app.response_class(
        response=json.dumps(assets, cls=DecimalEncoder),
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


@app.route("/api/v1/get_assets_info/", methods=['GET'])
def get_assets_info_api():
    asset_details = read_asset_details()
    return app.response_class(
        response=json.dumps(asset_details, cls=DecimalEncoder),
        status=200,
        mimetype='application/json'
    )


@app.route("/api/v1/issue_asset/", methods=['POST'])
def issue_asset_api():
    try:
        data = request.json
        asset_amount = data['asset_amount']
        token_amount = data.get('token_amount', 1)
        blind = data.get('blind', True)
        asset_name = data['asset_name']
        asset_icon_url = data['asset_icon_url']
        rpc_connection = get_rpc_connection()
        response = rpc_connection.issueasset(asset_amount, token_amount, blind)
        create_asset_entry(asset_id=response['asset'], asset_name=asset_name, asset_image_url=asset_icon_url)
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
    app.run(host="0.0.0.0", port=5000, debug=True)
