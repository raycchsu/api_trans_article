
from flask import render_template, Flask
import connexion
import uuid
from connexion.exceptions import BadRequestProblem
from datetime import datetime
import time
import traceback
import logging
import json

# log setting
logger = logging.getLogger('app_logger')
logger.setLevel(logging.INFO)

# Create handlers
c_handler = logging.StreamHandler()
c_format = logging.Formatter('%(asctime)s %(name)s - %(process)d - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)

# Add handlers to the logger
logger.addHandler(c_handler)

def get_timestamp():
    return datetime.now().strftime(("%Y-%m-%d %H:%M:%S"))

# Create the application instance
app = connexion.App(__name__, specification_dir='./')

# Read the swagger.yml file to configure the endpoints
app.add_api('swagger.yml')

def BadRequest(exception):
    api_name = str(connexion.request.url_rule).split('/')[-1]
    input_str = str(connexion.request.data, encoding = "utf-8").replace(' ','').replace('\n','')
    out = {"MWHEADER": {"MSGID": "","SOURCECHANNEL": "","TXNSEQ": "","RETURNCODE": "9998","RETURNDESC": "JSON格式錯誤"},"TRANRS": {}}

    logger.info('[ERROR] '+json.dumps(out))
    return out,400

app.add_error_handler(BadRequestProblem, BadRequest)

def serverError(exception):
    api_name = str(connexion.request.url_rule).split('/')[-1]
    input_str = str(connexion.request.data, encoding = "utf-8").replace(' ','').replace('\n','')
    out = {"MWHEADER": {"MSGID": "","SOURCECHANNEL": "","TXNSEQ": "","RETURNCODE": "9999","RETURNDESC": "其他未定義錯誤，請聯絡API負責人員"},"TRANRS": {'msg':exception}}
    logger.info('[ERROR] '+json.dumps(out))
    return out,500
app.add_error_handler(500,serverError)

@app.route('/')
def index():
    return "Server working..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    # app.run(debug=True)
