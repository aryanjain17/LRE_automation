# Monkey patch to trust all certificates
import gevent.monkey

gevent.monkey.patch_all()
##
import argparse
import requests
from requests.auth import HTTPBasicAuth
from os import environ as env
import os
from requests.structures import CaseInsensitiveDict
from requests_toolbelt import MultipartEncoder
from requests_toolbelt.utils import dump
import logging
import coloredlogs
import eventlet


# Logging with levels
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s [%(funcName)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger()
logger.setLevel("DEBUG")

# Create the parameters for LRE HTtp
LRE_URL = ""
user = ""
passw = ""
XML_CONTENT = "<Script xmlns=\"http://www.hp.com/PC/REST/API\"><TestFolderPath>Subject\\04 Final Scripts\\Shop</TestFolderPath><Overwrite>true</Overwrite><RuntimeOnly>true</RuntimeOnly></Script>"
LRE_HEADERS = CaseInsensitiveDict()
LRE_HEADERS["Expect"] = "100-continue"
LRE_HEADERS["Accept-Encoding"] = "gzip, deflate"
LRE_HEADERS["Cache-Control"] = "no-cache"
LRE_HEADERS["Accept-Language"] = "en-US,en;q=0.8,he;q=0.6,ru;q=0.4"
LRE_HEADERS["Content-Type"] = "multipart/form-data"
LRE_HEADERS["Accept"] = "application/json"

# https://admhelp.microfocus.com/lre/en/all/api_refs/Performance_Center_REST_API/Content/scripts.htm


def init_env():
    # See the agent environment vars
    for k, v in env.items():
        logger.debug(f"{k}={v}")

    if "LRE_URL" in env:
        LRE_URL = env["LRE_URL"]
        logger.debug(f"remote url is {LRE_URL}")
    if "LRE_USER" in env and "LRE_PASS" in env:
        user = env["LRE_USER"]
        passw = env["LRE_PASS"]
        token = HTTPBasicAuth(user, passw)
        logger.debug("username is %s" % user)
    #if token == ""
        #logger.log("<<<< Token was not generated >>>>")
    return LRE_URL, token

# The authenticate url to Login to LRE
def login_to_LRE(token, lre_url):
    url = lre_url + "LoadTest/rest/authentication-point/authenticate" # lre login restapi
    logger.debug("Logging into %s" % url)
    #  eventlet is used to timeout http request
    eventlet.monkey_patch()
    with eventlet.Timeout(10):
        resp = requests.get(url, auth=token)
        logger.debug("Log in to LRE response: %s" % str(resp))
        data = dump.dump_all(resp)
        logger.debug(data.decode("utf-8"))
        resp.raise_for_status()
    # Capture the SSO cookie
    for cookie in resp.cookies:
        if "sso" in cookie.name.lower():
            AuthCookie = cookie
    AuthCookie = resp.headers["Set-Cookie"].split(";")[0]
    logger.debug("session cookie - %s" % AuthCookie)
    return AuthCookie


def logout_LRE(lre_url, session):
    # Only send the headers with session token but not http auth creds.
    resp = requests.get(
        lre_url + "LoadTest/rest/authentication-point/logout", headers=LRE_HEADERS
    )
    data = dump.dump_all(resp)
    logger.debug(data.decode("utf-8"))


def upload_files(lre_url, sso_token):
    url = (
        lre_url
        + "LoadTest/rest/domains/UKConsumerOnlineDomain/projects/Digital/Scripts"
    )
    logger.debug("The upload url - %s" % url)
    # Adding the REST token to headers
    LRE_HEADERS["Cookie"] = sso_token
    logger.debug("rest token: %s" % sso_token)
    logger.debug("sending with headers: %s" % LRE_HEADERS)
    # The XMl Content to send Request
    lre_project_dir = SRC
    logger.info("The zip files are at %s" % lre_project_dir)
    for item in os.listdir(lre_project_dir):
        if item.endswith(".zip"):
            file_name = os.path.splitext(item)[0]
            logger.debug("Iter File in upload method: %s" % file_name)
            zip_path = lre_project_dir + "/" + item
            logger.debug("Zip path: %s" % zip_path)
            # xml_content = XML_CONTENT % file_name
            xml_content = XML_CONTENT
            logger.debug("XML Content %s" % xml_content)
            zip_content = MultipartEncoder(
                fields={
                    "aaa": (item, open(zip_path, "rb"), "application/x-zip-compressed"),
                    "": "%s" % xml_content,
                }
            )
            LRE_HEADERS["Content-Type"] = zip_content.content_type
            LRE_HEADERS["Accept-Encoding"] : "UTF-8"
            LRE_HEADERS["Accept"] : "*/*"
            LRE_HEADERS["Content-Type"] = zip_content.content_type
            logger.debug("content-type is %s" % zip_content.content_type)
            logger.debug("request headers are forged - %s" % LRE_HEADERS)
            resp = requests.post(
                url, headers=LRE_HEADERS, data=zip_content, verify=False
            )
            print("Upload Response: ---Begin----")
            print(resp.text)
            print("Upload Response: ---End----")
            data = dump.dump_all(resp)
            logger.debug(data.decode("utf-8"))
            if resp.status_code != 201:
                logger.debug("LRE response code: %s" % resp.status_code)
                raise
            logger.debug(
                "Upload is Successful with the HTTP Status %s" % resp.status_code
            )


# Monkey Patching for WFH + Proxy
def wfh_proxy():
    import functools

    orig_get = requests.get
    proxies = {"http": "http://localhost:3128", "https": "http://localhost:3128"}
    requests.get = functools.partial(orig_get, proxies=proxies)
    logger.debug("Proxies are enabled - %s" % proxies)
    coloredlogs.install(level=logging.DEBUG, logger=logger)


if __name__ == "__main__":

    # Get cli arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--source", help="zip files location")
    # parser.add_argument("--wfh", default=False, action=argparse.BooleanOptionalAction,help="WFH proxy usage")
    args = parser.parse_args()
    # Read the location of the zip files
    if args.source:
        SRC = args.source
        logger.debug("source dir is set to %s" % SRC)
    try:
        url, auth = init_env()
        session_token = login_to_LRE(auth, url)
        logger.debug("Session token: %s" % session_token)
        print("Beginning upload:")
        upload_files(url, session_token)
        logout_LRE(url, session_token)
    except Exception as e:
        logger.exception(" <<<< Fatal error in main loop >>>>: %s" % str(e))
        raise SystemExit("Script Error!")
