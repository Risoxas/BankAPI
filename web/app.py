"""Bank API

    """
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient('mongodb://db:27017')
db = client.BankAPI
users = db["Users"]


def user_exists(username):
    """Checks if user exists

    Args:
        username (string): user to check

    Returns:
        boolean: Returns true if exists false if it does'nt
    """
    if users.count_documents({"username": username}) == 0:
        return False
    return True


def verify_password(username, password):
    """Verifies password

    Args:
        username (string): username to check password
        password (string): password to match

    Returns:
        boolean: True if password matches false if it does'nt
    """
    if not user_exists(username):
        return False
    hashed_pw = users.find_one({"username": username})["password"]
    if bcrypt.hashpw(password.encode("utf-8"), hashed_pw) == hashed_pw:
        return True
    return False


def get_balance(username):
    """Gets the current balance of user

    Args:
        username (string): Username to check

    Returns:
        number: amount of money in account
    """
    cash = users.find_one({"username": username})["balance"]
    return cash


def get_debt(username):
    """Get total debt of user

    Args:
        username (string): Username to check debt

    Returns:
        number: amount of debt in user account
    """
    debt = users.find_one({"username": username})["debt"]
    return debt


def format_response(status, message):
    """Formats the json return

    Args:
        status (number): Http status code to send
        message (string): Message included in response

    Returns:
        object: formatted json response
    """
    return {
        "status": status,
        "message": message
    }


def verify_credentials(username, password):
    """Verifies user credentials

    Args:
        username (string): username to match
        password (string): password to match

    Returns:
        tuple: object response, matching result
    """
    if not user_exists(username):
        return format_response(301, "Invalid Username"), True
    correct_pw = verify_password(username, password)
    if not correct_pw:
        return format_response(302, "Incorrect Password"), True

    return None, False


def update_account(username, balance):
    """Updates balance in account

    Args:
        username (string): username to add money to
        balance (number): amount of money to add
    """
    users.update_one({"username": username}, {"$set": {"balance": balance}})


def update_debt(username, debt):
    """Update amount of debt in account

    Args:
        username (string): user to update
        debt (number): amount of det to add
    """
    users.update_one({"username": username}, {"$set": {"debt": debt}})


class Register(Resource):
    """Registers user in API

    Args:
        Resource (Resource): flask_restful Resource class
    """

    def post(self):
        """Post request to register user

        Returns:
            Object: Json response
        """
        posted_data = request.get_json()
        username = posted_data["username"]
        password = posted_data["password"]

        if user_exists(username):
            return jsonify(format_response(301, "Invalid Username"))

        hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        users.insert_one({
            "username": username,
            "password": hashed_pw,
            "balance": 0,
            "debt": 0
        })

        return jsonify(format_response(200, "You successfully signed up for the API"))


class Add(Resource):
    """Adds money to the account

    Args:
        Resource (class): flask_restful Resource class
    """

    def post(self):
        """Post Request

        Returns:
            Object: json response
        """
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        if money <= 0:
            return jsonify(format_response(
                304, "The money amount entered must be greater than zero"))

        cash = get_balance(username)

        money -= 1

        bank_cash = get_balance("BANK")
        update_account("BANK", bank_cash+1)
        update_account(username, cash+money)

        return jsonify(format_response(200, "Amount added successfully to account"))


class Transfer(Resource):
    """Transfer money between accounts

    Args:
        Resource (class): flask_restful Resource class
    """

    def post(self):
        """Post Request

        Returns:
            Object: json Response
        """
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        destination = posted_data["destination"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        if not user_exists(destination):
            return jsonify(format_response(301, "Invalid destination account"))

        sender_cash = get_balance(username)
        if sender_cash <= 0:
            return jsonify(304, "Not enough money in account, please add more money")

        receiver_cash = get_balance(destination)
        bank_cash = get_balance("BANK")

        update_account("BANK", bank_cash+1)
        update_account(destination, receiver_cash + money - 1)
        update_account(username, sender_cash - money)

        return jsonify(format_response(200, "Successful transaction"))


class Balance(Resource):
    """Checks user balance

    Args:
        Resource (class): flask_restful Resource class
    """

    def post(self):
        """Post Request

        Returns:
            Object: json Response
        """
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        return users.find({"username": username}, {
            "password": 0, "_id": 0})[0]


class TakeLoan(Resource):
    """Class to request a loan

    Args:
        Resource (class): flask_restful Resource class
    """

    def post(self):
        """Post Request

        Returns:
            Object: json Response
        """
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        cash = get_balance(username)
        debt = get_debt(username)
        update_account(username, cash+money)
        update_debt(username, debt + money)

        return jsonify(format_response(200, "Loan added succesfully"))


class PayLoan(Resource):
    """Class to reduce debt

    Args:
        Resource (class): flask_restful Resource class
    """

    def post(self):
        """Post request

        Returns:
            Object: json Response
        """
        posted_data = request.get_json()

        username = posted_data["username"]
        password = posted_data["password"]
        money = posted_data["amount"]

        ret_json, error = verify_credentials(username, password)

        if error:
            return jsonify(ret_json)

        cash = get_balance(username)

        if cash < money:
            return jsonify(format_response(303, "Not enough money in account"))

        debt = get_debt(username)
        update_account(username, cash - money)
        update_debt(username, debt - money)

        return jsonify(format_response(200, "Payment processed"))


api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/loan')
api.add_resource(PayLoan, '/pay')

if __name__ == '__main__':
    app.run(host='0.0.0.0')
