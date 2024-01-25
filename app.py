import flask

app = flask.Flask(__name__)

app.config.from_prefixed_env()


@app.route("/")
def hello():
    return flask.jsonify(app.config["RABBITMQ_URIS"])
