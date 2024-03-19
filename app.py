#!/usr/bin/env python3

import io
import os
import sys
import subprocess
import datetime
import json

from flask import Flask, render_template, request, redirect, url_for, make_response, send_file

# import logging
import sentry_sdk
from sentry_sdk.integrations.flask import (
    FlaskIntegration,
)  # delete this if not using sentry.io

# from markupsafe import escape
import pymongo
from pymongo.errors import ConnectionFailure
from bson.objectid import ObjectId
from dotenv import load_dotenv

# import BeautifulSoup for table data extraction
# import bs4

# load credentials and configuration options from .env file
# if you do not yet have a file named .env, make one based on the template in env.example
load_dotenv(override=True)  # take environment variables from .env.

# initialize Sentry for help debugging... this requires an account on sentrio.io
# you will need to set the SENTRY_DSN environment variable to the value provided by Sentry
# delete this if not using sentry.io
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    # enable_tracing=True,
    # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions.
    # We recommend adjusting this value in production.
    # profiles_sample_rate=1.0, # Parameter not recognized
    integrations=[FlaskIntegration()],
    # traces_sample_rate=1.0, # duplictated definition, cause error
    send_default_pii=True,
)

# instantiate the app using sentry for debugging
app = Flask(__name__)

# # turn on debugging if in development mode
# app.debug = True if os.getenv("FLASK_ENV", "development") == "development" else False

# try to connect to the database, and quit if it doesn't work
try:
    cxn = pymongo.MongoClient(os.getenv("MONGO_URI"))
    db = cxn[os.getenv("MONGO_DBNAME")]  # store a reference to the selected database

    # verify the connection works by pinging the database
    cxn.admin.command("ping")  # The ping command is cheap and does not require auth.
    print(" * Connected to MongoDB!")  # if we get here, the connection worked!
except ConnectionFailure as e:
    # catch any database errors
    # the ping command failed, so the connection is not available.
    print(" * MongoDB connection error:", e)  # debug
    sentry_sdk.capture_exception(e)  # send the error to sentry.io. delete if not using
    sys.exit(1)  # this is a catastrophic error, so no reason to continue to live

# Define constants.
BYTE_USAGE = "size"
COUNT = "count"

# Registered keys of a word.
KEY = "key"
NOTES = "notes"
PRONOUNCE = "pronounciation"
LEVEL = "proficiency"
DETIAL = "description"

WORD_KEYS = [
    KEY, 
    NOTES, 
    PRONOUNCE, 
    LEVEL, 
    DETIAL
]

PAGE_KEY = "key[]"
PAGE_NOTES = "notes[]"
PAGE_PRONOUNCE = "pronounciation[]"
PAGE_LEVEL = "proficiency[]"
PAGE_DETIAL = "description[]"

PAGE_WORD_KEYS = [
    PAGE_KEY, 
    PAGE_NOTES, 
    PAGE_PRONOUNCE, 
    PAGE_LEVEL, 
    PAGE_DETIAL
]

# set up the routes


@app.route("/")
def home():
    """
    Route for the home page.
    Simply returns to the browser the content of the index.html file located in the templates folder.
    """
    return render_template("index.html")


@app.route("/collections")
def get_collections():
    """
    Route for GET requests to the read page.
    Displays some information for the user with links to other pages.
    """
    # Get name of all collections.
    colls: list[str] = db.list_collection_names()

    # Create container to store info of each word list.
    colls_info: dict[str : dict[str : int]] = {}
    
    # Get the size of each wordlist.
    for coll in colls:
        coll_info = db.command("collstats", coll)
        colls_info[coll] = {BYTE_USAGE : coll_info[BYTE_USAGE], 
                      COUNT : coll_info[COUNT]}
    
    return render_template("collections.html", 
                           items=colls_info, 
                           res_num=len(colls_info))  # render the read template


@app.route("/create")
def create():
    """
    Route for GET requests to the create page.
    Displays a form users can fill out to create a new document.
    """
    return render_template("create.html")  # render the create template


@app.route("/create", methods=["POST"])
def create_post():
    """
    Route for POST requests to the create page.
    Accepts the form submission data for a new document and saves the document to the database.
    """
    # Create container to store data in words table.
    data = {}
    
    # Extract data from words table.
    for key in PAGE_WORD_KEYS:
        data[key] = request.form.getlist(key)
    
    # Get number of words.
    num_of_words = len(data[key])
    
    # Build the words list.
    words = []

    # Group data by row.
    for row_index in range(num_of_words):
        word = {KEY : data[PAGE_KEY][row_index], 
                NOTES : data[PAGE_NOTES][row_index], 
                PRONOUNCE : data[PAGE_PRONOUNCE][row_index], 
                LEVEL : int(data[PAGE_LEVEL][row_index]), 
                DETIAL : data[PAGE_DETIAL][row_index], 
                "created": datetime.datetime.now()}
        words.append(word)
    
    # Get words list name.
    name = request.form["name"]

    # Check if collection already exists.
    if name in db.list_collection_names():
        msg = "Creation Failed: a word list with the same name already exists!"
        return render_template("create.html", 
                               msg=msg, 
                               list_name=name, 
                               docs=words)

    # Create a new collection.
    db.create_collection(name)
    new_coll = db[name]

    # Add data to collection.
    if words:
        new_coll.insert_many(words)

    return redirect(
        url_for("get_collections")
    )  # tell the browser to make a request for the /collections route


@app.route("/edit/<collection>")
def edit(collection):
    """
    Route for GET requests to the edit page.
    Displays a form users can fill out to edit an existing record.

    Parameters:
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    docs = db[collection].find().sort("created", 1)
    # doc = db.exampleapp.find_one({"_id": ObjectId(collection)})
    return render_template(
        "edit.html", collection=collection, docs=docs
    )  # render the edit template

@app.route("/rename/<old_name>/<new_name>")
def rename(old_name, new_name):
    """
    Rename an existing collection.
    
    Parameters:
    old_name (str): The current name of the collection.
    new_name (str): The new name to be renamed.
    """
    if new_name in db.list_collection_names():
        return "Failed: collection name already exists.", 404
    
    db[old_name].rename(new_name)
    return "Succeed", 200

@app.route("/edit/<collection>", methods=["POST"])
def edit_post(collection):
    """
    Route for POST requests to the edit page.
    Accepts the form submission data for the specified 
        document and updates the document in the database.

    Parameters:
    collection (str): The MongoDB collection to be saved.
    """
    # Create container to store data in words table.
    data = request.json
    coll = db[collection]

    # Update target document.
    for doc in data['update']:
        coll.update_one({ "_id": ObjectId(doc['_id']) }, 
                        { "$set": doc['info'] })
    
    # Insert documents (cannot be empty).
    if data['insert']:
        coll.insert_many(data['insert'])

    return "Succeed"

@app.route("/save/<collection>/", methods=["POST"])
@app.route("/save/<collection>/<mongoid>", methods=["POST"])
def save_document(collection, mongoid=""):
    """
    Route for POST requests to update/save a document.
    Accepts the row data for the specified document and updates the document in the database.

    Parameters:
    collection (str): collection (Collection): The collection to be modified.
    mongoid (str): The MongoDB ObjectId of the record to be edited.
    """
    # Extract document to be saved.
    doc = request.json

    if collection not in db.list_collection_names():
        return "Failed: target collection does not exist."

    # Get the collection to be modified.
    coll = db[collection]

    if mongoid:
        # Update existing document.
        coll.update_one({ "_id": ObjectId(mongoid) }, 
                        { "$set": doc })
        print(coll.find_one({ "_id": ObjectId(mongoid) }))
        return "Succeed"

    # Add create time.
    doc['created'] = datetime.datetime.now()

    # Add new document to database.
    doc_id = coll.insert_one(doc).inserted_id

    return "Succeed", str(doc_id)


@app.route("/delete/<collection>")
def delete(collection):
    """
    Route for GET requests to the delete page.
    Deletes the specified collection from the database, and then redirects the browser to the read page.

    Parameters:
    collection (str): The MongoDB Collection to be deleted.
    """
    # Delete the collection.
    db[collection].drop()
    # db.exampleapp.delete_one({"_id": ObjectId(collection)})
    return redirect(
        url_for("get_collections")
    )  # tell the web browser to make a request for the /get_collections route.

@app.route("/delete/<collection>/<mongoid>")
def delete_document(collection, mongoid):
    """
    Route for GET requests to delete an document.
    Delete a document, return true if succeed, false record not found.
    
    Parameters:
    collection (Collection): The collection that contains 
        the document to be deleted.
    mongoid (str): The MongoDB ObjectId of the document to be deleted.
    """
    filter = {"_id": ObjectId(mongoid)}
    
    if not db[collection].find_one(filter):
        # Document not exist.
        return "Failed: the document does not exist!"
    
    # Delete the matched document.
    db[collection].delete_one(filter)

    return "Succeed"

@app.route("/download/<collection>")
def download(collection):
    """
    Route for GET requests to download the specified collection.
    Return the data in the collection as a file to be download.
    
    Parameters:
    collection (Collection): the collection to be downloaded."""
    # Define filter.
    filter = {"_id": 0, 
              "created": 0 }
    
    # Extract data from the collection.
    data = list(db[collection].find({}, filter))

    # Convert data to JSON stirng.
    content = json.dumps(data, 
                         ensure_ascii=False, 
                         indent=4)
    
    # Get filename.
    filename = f"{collection}.json"
    print(filename)

    return send_file(io.BytesIO(content.encode()), 
                     mimetype="application/json", 
                     as_attachment=True, 
                     attachment_filename=filename)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    GitHub can be configured such that each time a push is made to a repository, GitHub will make a request to a particular web URL... this is called a webhook.
    This function is set up such that if the /webhook route is requested, Python will execute a git pull command from the command line to update this app's codebase.
    You will need to configure your own repository to have a webhook that requests this route in GitHub's settings.
    Note that this webhook does do any verification that the request is coming from GitHub... this should be added in a production environment.
    """
    # run a git pull command
    process = subprocess.Popen(["git", "pull"], stdout=subprocess.PIPE)
    pull_output = process.communicate()[0]
    # pull_output = str(pull_output).strip() # remove whitespace
    process = subprocess.Popen(["chmod", "a+x", "flask.cgi"], stdout=subprocess.PIPE)
    chmod_output = process.communicate()[0]
    # send a success response
    response = make_response(f"output: {pull_output}", 200)
    response.mimetype = "text/plain"
    return response


@app.errorhandler(Exception)
def handle_error(e):
    """
    Output any errors - good for debugging.
    """
    return render_template("error.html", error=e)  # render the edit template


# run the app
if __name__ == "__main__":
    # logging.basicConfig(filename="./flask_error.log", level=logging.DEBUG)
    app.run(load_dotenv=True)
