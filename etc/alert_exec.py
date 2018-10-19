import requests, json, sys, time, os, argparse

#suppress TLS certificate check omit warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ************************ PARAMETER DEFINITIONS: *************************#
# API url endpoints for SpectX and StackStorm:
sx_api_root = "http://localhost:8388/API/v1.0/"
ss_api_root = "https://127.0.0.1/api/v1/webhooks/"

# API access credentials:
# SpectX API access key must be set to $SX_API_KEY environment variable!
# StackStorm API access key must be set to $ST2_API_KEY environment variable!

# SpectX query path and webhook url are specified with command line arguments:
# usage: alert_exec.py [-h] -qp SX_QUERY -wh WEBHOOK_URL
#
# SpectX query path and webhook url
#
# optional arguments:
# -h, --help       show this help message and exit
# -qp SX_QUERY     path and name of SpectX query script
# -wh WEBHOOK_URL  StackStorm API endpoint (webhook url)


def exec_sx_stored_query(sx_query):
    headers = {
        "Authorization": "Bearer " + os.getenv("SX_API_KEY", ""),
        "Accept": "application/json"
    }
    prm = {
        "scriptPath":sx_query
    }
    http_resp = requests.post(sx_api_root, headers=headers, params=prm)

    if http_resp.status_code != 200:
        #post a notification to Slack channel using spect_failure webhook rule
        rc = http_resp.json()
        rc['status_code'] = http_resp.status_code
        rc['script'] = sx_query
        exec_ss_webhook("spectx_failure", rc)
        exit(1)
    return http_resp


def exec_ss_webhook(url, data):
    headers = {"Content-Type" : "application/json",
               "St2-Api-Key" : os.getenv("ST2_API_KEY", "")
    }
    resp = requests.post(ss_api_root + url, headers=headers, data=json.dumps(data), verify=False)
    if resp.status_code != 202:  #StackStorm API returns 202 on success
        Fatal("%s webhook request failed: StackStorm API returned %i" % resp.status_code)


def parseCmdline():
    if len(sys.argv)-1 != 2:
        Fatal("Unexpected number of arguments " + str(len(sys.argv)))

    skip=0
    # Parse command line
    for i in range(1, len(sys.argv)):
        if not skip:
            if   sys.argv[i][:3] == "-sx": sx_query = sys.argv[i]
            elif sys.argv[i][:3] == "-wh": webhook = sys.argv[i]
            else: Fatal("unexpected argument '%s'" % sys.argv[i])
        else: skip = 0

    if(len(sx_query)==0 or len(webhook)==0):
        Fatal("invalid arguments %s %s" % (sx_query, webhook))

    return (sx_query, webhook)

def Fatal(msg):
    sys.stderr.write("%s: %s\n" % (time.strftime('%Y-%m-%d %H:%M:%S %Z'), msg))
    sys.exit(1)

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('-qp', type=str, required=True, help='path and name of SpectX query script', dest='sx_query')
    parser.add_argument('-wh', type=str, required=True, help='StackStorm API endpoint (webhook url)', dest='webhook_url')

    args = parser.parse_args()

    result = exec_sx_stored_query(args.sx_query).json()
    rows = len(result)
    if(rows > 0):
        for row in result:
            exec_ss_webhook(args.webhook_url, row)

if __name__ == "__main__":
    main()
