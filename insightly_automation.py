#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from __future__ import print_function

import json
import logging
import logging.config
import os
import re
import shelve

from datetime import datetime
from copy import copy
from os.path import abspath, dirname, exists, join
from shutil import copyfile
from textwrap import dedent

import requests

if not exists('insightly_automation_config.py'):
    print(u'*** Creating default config file insightly_automation_config.py')
    copyfile('insightly_automation_config.py.example', 'insightly_automation_config.py')

import insightly_automation_config as config


def insightly_get(url, auth):
    """ Send GET response. Raise exception if response status code is not 200. """
    response = requests.get('https://api.insight.ly/v2.1' + url, auth=auth)
    if response.status_code != 200:
        err = Exception('Insightly api GET error: Http status %s. Url:\n%s' % (response.status_code, url))
        logging.critical(err)
        raise err
    return json.loads(response.content)


def insightly_put(url, auth, **kwargs):
    """ Send PUT response. Raise exception if response status code is not 200. """
    response = requests.put("https://api.insight.ly/v2.1" + url, auth=auth, **kwargs)
    if response.status_code != 200:
        err = Exception('Insightly api PUT error: Http status %s. Url:\n%s' % (response.status_code, url))
        logging.critical(err)
        raise err
    return json.loads(response.content)


def configure():
    """
    Apply configuration from config.py
    """

    if hasattr(config, 'LOG_FILE'):
        LOG_FILE = abspath(config.LOG_FILE)
        print('Log messages will be sent to %s' % LOG_FILE)
    else:
        LOG_FILE = '/var/log/insightly_automation.log'
        print('Log messages will be sent to %s. You can change LOG_FILE in the config.' % LOG_FILE)

    # Test write permissions in the log file directory.
    permissons_test_path = join(dirname(LOG_FILE), 'insightly_test.log')
    try:
        with open(permissons_test_path, 'w+') as test_file:
            test_file.write('test')
        os.remove(permissons_test_path)
    except (OSError, IOError) as e:
        msg = '''\
            Write to the "%s/" directory failed. Please check permissions or change LOG_FILE config.
            Original error was: %s.''' % (dirname(LOG_FILE), e)
        raise Exception(dedent(msg))

    LOG_LEVEL = getattr(config, 'LOG_LEVEL', 'INFO')

    logging.config.dictConfig({
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s.py: %(message)s',
                'datefmt': '<%Y-%m-%d %H:%M:%S>'
            },
            'simple': {'format': '%(levelname)s %(module)s.py: %(message)s'},
        },
        'handlers': {
            'log_file': {
                'level': LOG_LEVEL,
                'class': 'logging.handlers.WatchedFileHandler',
                'filename': LOG_FILE,
                'formatter': 'verbose'
            },
            'console': {
                'level': LOG_LEVEL,
                'class': 'logging.StreamHandler',
                'formatter': 'simple'
            },
        },
        'loggers': {
            '': {'handlers': ['log_file', 'console'], 'level': LOG_LEVEL},
        }
    })

    try:
        from insightly_automation_config import INSIGHTLY_API_KEY
        from insightly_automation_config import LEAD_TAG_ONLY
    except Exception as e:
        logging.critical('Please set required config varialble in insightly_automation_config.py:\n%s', str(e))
        raise

    if not re.match(r'\w{8}-\w{4}-\w{4}-\w{4}-\w{12}', INSIGHTLY_API_KEY):
        err = Exception('INSIGHTLY_API_KEY has wrong format "%s", please set the right value in insightly_automation_config.py' % INSIGHTLY_API_KEY)
        logging.critical(err)
        raise err


from pprint import pprint


def fix_leads():
    """
    """
    #db = shelve.open('db.shelve')

    # Tuple (user, password) for request authentication. User should be the api key, password is empty.
    insightly_auth = (config.INSIGHTLY_API_KEY, '')

    #lead = insightly_get('/leads/8808249', insightly_auth)
    #server_opportunities = insightly_get("/opportunities/10719115", insightly_auth)
    #links = server_opportunities['LINKS']
    #contacts = insightly_get("/Contacts", insightly_auth)
    #orgs = insightly_get("/organisations", insightly_auth)
    #db['last_poll'] = now

    fields = insightly_get('/CustomFields', insightly_auth)
    titles = [x for x in fields if x['FIELD_FOR'] == 'CONTACT' and 'title' in x['FIELD_NAME'].lower()]

    if len(titles) > 1:
        logging.error('More than one title custom field.')
        return
    title_id = titles[0]['CUSTOM_FIELD_ID']

    leads = insightly_get('/leads?includeConverted=true', insightly_auth)

    logging.info('%d leads found.' % len(leads))

    tag_filter = getattr(config, 'LEAD_TAG_ONLY', None)

    for lead in leads:
        if not lead['CONVERTED']:
            continue

        if tag_filter:
            for tag in lead['TAGS']:
                if tag['TAG_NAME'] == tag_filter:
                    break
            else:
                # No matching tag found, skip this lead.
                continue

        ##if lead['LEAD_ID'] in db['fixed_leads']:
            ##continue

        #### The lead was converted, but not yet fixed. Let's fix it.

        ##'CONVERTED_CONTACT_ID': 169756128,
        ##'CONVERTED_DATE_UTC': u'2016-05-05 11:52:15',
        ##opportunity = insightly_get("/opportunities/%s" % lead['CONVERTED_OPPORTUNITY_ID'], insightly_auth)

        contact_url = "/contacts/%s" % lead['CONVERTED_CONTACT_ID']
        contact = insightly_get(contact_url, insightly_auth)
        title = [x for x in contact['CUSTOMFIELDS'] if x['CUSTOM_FIELD_ID'] == title_id]
        if title:
            title = title[0]
        else:
            title = {'CUSTOM_FIELD_ID': title_id}
            contact['CUSTOMFIELDS'].append(title)

        if title.get('FIELD_VALUE'):
            continue

        title['FIELD_VALUE'] = lead['TITLE']

        insightly_put(contact_url, insightly_auth, json=contact)
        logging.info('Contact #%d title updated to "%s"' % (contact['CONTACT_ID'], title['FIELD_VALUE']))

        ### Store the lead ID in fixed_leads set.
        ##db['fixed_leads'] = db['fixed_leads'] | {lead['LEAD_ID']}

    ##server_lead_ids = set(x['LEAD_ID'] for x in leads if lead['CONVERTED'])
    ##new_ = db['opportunities_ids'].difference(server_opportunities_ids)


def main():
    configure()
    fix_leads()


if __name__ == '__main__':
    main()
