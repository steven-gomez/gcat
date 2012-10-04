#!/usr/bin/python

from oauth2client.client import  OAuth2WebServerFlow, OAuth2Credentials
from oauth2client.file import Storage
from apiclient.discovery import build
from apiclient import errors
import httplib2

import argparse
import sys, os.path
import re
import logging

from operator import itemgetter
import webbrowser
import yaml, json, pprint


"""
logging set up
"""
LOGLEVELS = {'DEBUG': logging.DEBUG,
             'INFO': logging.INFO,
             'WARNING': logging.WARNING,
             'ERROR': logging.ERROR,
             'CRITICAL': logging.CRITICAL}  
root_logger = logging.getLogger()
ch = logging.StreamHandler()
formatter = logging.Formatter('[%(levelname)s]\t[%(filename)s:%(funcName)s:%(lineno)d]\t%(message)s')
ch.setFormatter(formatter)
root_logger.addHandler(ch)
root_logger.setLevel(logging.DEBUG)


def get_file(args):
    service = get_service(args)
    files = service.files()
    try:
        res = files.list().execute()
    except errors.HttpError, error:
        logging.error('An error occurred: %s', exc_info=error)
        raise error

    idx = map(itemgetter('title'), res['items']).index(args.title)
    file = res['items'][idx]
    content = download(service, file)
    return content

def get_service(args):
    flow = OAuth2WebServerFlow(client_id=args.client_id,
                               client_secret=args.client_secret,
                               scope=args.scope,
                               redirect_uri=args.redirect_uri)

    credentials = get_credentials(args)

    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('drive', 'v2', http=http)
    return service


def get_credentials(args):
    storage = Storage(args.store)
    credentials = storage.get()
    if not credentials:
        # get the credentials the hard way
        auth_url = flow.step1_get_authorize_url()
        webbrowser.open(auth_url)
        code = raw_input('go to:\n\n\t%s\n\nand enter in the code displayed:' % auth_url)
        credentials = flow.step2_exchange(code)
        storage.put(credentials)

    #pprint.pprint(json.loads(credentials.to_json()), indent=2)
    if credentials.access_token_expired:
        logging.info('refreshing token')
        refresh_http = httplib2.Http()
        credentials.refresh(refresh_http) 
    return credentials


def download(service, file):
    logging.debug('file.viewkeys(): %s', pprint.pformat(file.viewkeys()))
    # download_url = file.get('downloadUrl') # not present for some reason
    download_url_pdf = file.get('exportLinks')['application/pdf']
    download_url = re.sub('pdf$', 'csv', download_url_pdf)
    if download_url:
        resp, content = service._http.request(download_url)
        if resp.status == 200:
            logging.debug('Status: %s', resp)
            return content
        else:
            logging.error('An error occurred: %s' % resp)
            return None
    else:
        # The file doesn't have any content stored on Drive.
        logging.error('file does not have any content stored on Drive')
        return None    


def merge_config(args, yaml_name):
    logging.debug('merging config from file: %s', yaml_name)
    config = yaml.load(open(yaml_name, 'r'))
    for k, v in config.items():
        if not hasattr(args,k) or getattr(args, k) is None:
            setattr(args,k,v)


class Join(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, ' '.join(values))


def parse_args():
    parser = argparse.ArgumentParser(description='print a google spreadsheet to stdout')
    parser.add_argument('--store',
                        default=os.path.expanduser('~/.gcat/store'),
                        help='location where gcat will store file specific credentials')
    parser.add_argument('--config',
                        default=os.path.expanduser('~/.gcat/config'),
                        help='a yaml file specifying the client_id, client_secret, scope, and redirect_uri')
    parser.add_argument('--client_id',
                        help='google api client id. this can be found at the google api console.  Note that'
                        'you first need to register your client as an "installed application" at the console'
                        ' as well (code.google.com/apis/console)')
    parser.add_argument('--client_secret',
                        help='google api client secret. this can be found at the google api console.  Note that'
                        'you first need to register your client as an "installed application" at the console'
                        ' as well (code.google.com/apis/console)')
    parser.add_argument('--scope',
                        help='list of scopes for which your client is authorized')
    parser.add_argument('--redirect_uri',
                        default='urn:ietf:wg:oauth:2.0:oob',
                        help='google api redirect URI. this can be found at the google api console under the \"Redirect URI\"'
                        'section.  By default a client if assigned two valid redirect URIs: urn:ietf:wg:oauth:2.0:oob '
                        'and http://localhostl.  use the urn:ietf:wg:oauth:2.0:oob unless you are doing something fancy.'
                        'see https://developers.google.com/accounts/docs/OAuth2InstalledApp for more info')
    parser.add_argument('title',
                        nargs='+',
                        action=Join,
                        help='The name of the google drive file in question.  If the name has spaces, gcat will do the '
                        ' right thing and treat a sequence of space delimited words as a single file name')
    args = parser.parse_args()
    merge_config(args, args.config)
    logging.info('\n' + pprint.pformat(vars(args)))
    return args
    

def write(file_obj):
    pass


def main():
    args = parse_args()
    file = get_file(args)
    print file


if __name__ == '__main__':
    main()