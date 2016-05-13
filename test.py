# -*- coding: UTF-8 -*-
# You can run this test script with `python -m unittest test`

from textwrap import dedent
from unittest import TestCase

from mock import Mock, patch

import insightly_automation
import insightly_automation_config as config


CUSTOM_FIELD_TEMPLATE = {
    u'CUSTOM_FIELD_ID': u'CONTACT_FIELD_1',
    u'CUSTOM_FIELD_OPTIONS': [],
    u'DEFAULT_VALUE': None,
    u'FIELD_FOR': u'CONTACT',
    u'FIELD_HELP_TEXT': None,
    u'FIELD_NAME': u'title',
    u'FIELD_TYPE': u'TEXT',
    u'GROUP_ID': None,
    u'ORDER_ID': 1}

LEAD_TEMPLATE = {
    u'ADDRESS_CITY': None,
    u'ADDRESS_COUNTRY': None,
    u'ADDRESS_POSTCODE': None,
    u'ADDRESS_STATE': None,
    u'ADDRESS_STREET': None,
    u'CONVERTED': True,
    u'CONVERTED_CONTACT_ID': 1,
    u'CONVERTED_DATE_UTC': u'2016-05-05 11:52:15',
    u'CONVERTED_OPPORTUNITY_ID': 1,
    u'CONVERTED_ORGANIZATION_ID': 1,
    u'CUSTOMFIELDS': [],
    u'DATE_CREATED_UTC': u'2016-05-05 11:49:30',
    u'DATE_UPDATED_UTC': u'2016-05-05 13:06:24',
    u'EMAIL_ADDRESS': u'someuniquename@example.com',
    u'EMAIL_LINKS': [],
    u'EMPLOYEE_COUNT': None,
    u'EVENT_LINKS': [],
    u'FAX_NUMBER': None,
    u'FILE_ATTACHMENTS': [],
    u'FIRST_NAME': u'ffffname',
    u'IMAGE_URL': u'http://s3.amazonaws.com/insightly.userfiles/643478/',
    u'INDUSTRY': None,
    u'LAST_NAME': u'llllname',
    u'LEAD_DESCRIPTION': None,
    u'LEAD_ID': 8808249,
    u'LEAD_RATING': None,
    u'LEAD_SOURCE_ID': 920659,
    u'LEAD_STATUS_ID': 911526,
    u'MOBILE_PHONE_NUMBER': None,
    u'NOTE_LINKS': [],
    u'ORGANIZATION_NAME': u'orglead',
    u'OWNER_USER_ID': 1093279,
    u'PHONE_NUMBER': None,
    u'RESPONSIBLE_USER_ID': 1093279,
    u'SALUTATION': None,
    u'TAGS': [],
    u'TASK_LINKS': [],
    u'TITLE': u'leadtit',
    u'VISIBLE_TEAM_ID': None,
    u'VISIBLE_TO': u'EVERYONE',
    u'VISIBLE_USER_IDS': None,
    u'WEBSITE_URL': None}


CONTACT_TEMPLATE = {
    u'ADDRESSES': [],
    u'BACKGROUND': None,
    u'CONTACTINFOS': [{
        u'CONTACT_INFO_ID': 289433969,
        u'DETAIL': u'someuniquename@example.ru',
        u'LABEL': u'WORK',
        u'SUBTYPE': None,
        u'TYPE': u'EMAIL'}],
    u'CONTACTLINKS': [],
    u'CONTACT_ID': 1,
    u'CUSTOMFIELDS': [{
        u'CUSTOM_FIELD_ID': u'CONTACT_FIELD_1',
        u'FIELD_VALUE': u'ttit'}],
    u'DATES': [],
    u'DATE_CREATED_UTC': u'2016-05-05 11:52:15',
    u'DATE_UPDATED_UTC': u'2016-05-05 11:52:15',
    u'DEFAULT_LINKED_ORGANISATION': None,
    u'EMAILLINKS': [],
    u'FIRST_NAME': u'ffffname',
    u'IMAGE_URL': u'http://s3.amazonaws.com/insightly.userfiles/643478/',
    u'LAST_NAME': u'llllname',
    u'LINKS': [
        {
            u'CONTACT_ID': 1,
            u'DETAILS': None,
            u'LINK_ID': 107536713,
            u'OPPORTUNITY_ID': None,
            u'ORGANISATION_ID': 80006270,
            u'PROJECT_ID': None,
            u'ROLE': None,
            u'SECOND_OPPORTUNITY_ID': None,
            u'SECOND_PROJECT_ID': None},
        {
            u'CONTACT_ID': 1,
            u'DETAILS': None,
            u'LINK_ID': 107536714,
            u'OPPORTUNITY_ID': 10719115,
            u'ORGANISATION_ID': None,
            u'PROJECT_ID': None,
            u'ROLE': None,
            u'SECOND_OPPORTUNITY_ID': None,
            u'SECOND_PROJECT_ID': None},
        {
            u'CONTACT_ID': 1,
            u'DETAILS': None,
            u'LINK_ID': 107615891,
            u'OPPORTUNITY_ID': 10302953,
            u'ORGANISATION_ID': None,
            u'PROJECT_ID': None,
            u'ROLE': u'roleeee',
            u'SECOND_OPPORTUNITY_ID': None,
            u'SECOND_PROJECT_ID': None}],
    u'OWNER_USER_ID': 1093279,
    u'SALUTATION': None,
    u'TAGS': [],
    u'VISIBLE_TEAM_ID': None,
    u'VISIBLE_TO': u'EVERYONE',
    u'VISIBLE_USER_IDS': None
}


class InsightlyFakeServer(object):
    """
    Trivial fake server will look up requested GET url in dict of configured responses (self.get_response).

    You can provide initial get_response dict on init:
    >>> fake_insightly = InsightlyFakeServer(get_response={'/CustomFields': [{'x': 'y'}, {'a': 'b'}]})

    Or you can later add items to the response dict:
    >>> fake_insightly.get_response['/contacts/1'] = {'id': 1, 'name': 'lol'})

    Then you should patch `insightly_get()` function with this server's get() method:
    >>> patch('insightly_automation.insightly_get', Mock(side_effect=fake_insightly.get)).start()

    """
    def __init__(self, get_response=None):
        self.get_response = get_response or {}

    def get(self, url, *args, **kwargs):
        if url not in self.get_response:
            raise Exception('Unknown fake url "%s"' % url)
        return self.get_response[url]


class TagFilterTestCase(TestCase):
    # If `LEAD_TAG_ONLY` config variable is set, then only leads with this tag may be modified.

    def setUp(self):
        # GIVEN insightly server with custom field 'title'
        self.fake_insightly = InsightlyFakeServer(get_response={'/CustomFields': [CUSTOM_FIELD_TEMPLATE]})
        patch('insightly_automation.insightly_get', Mock(side_effect=self.fake_insightly.get)).start()
        patch('insightly_automation.insightly_put', Mock()).start()
        # AND config with `LEAD_TAG_ONLY` set
        patch('insightly_automation.config.LEAD_TAG_ONLY', 'lol2').start()

    def tearDown(self):
        patch.stopall()

    def test_changed_bid_amount(self):
        # GIVEN two converted leads on server
        self.fake_insightly.get_response['/leads?includeConverted=true'] = [
            dict(LEAD_TEMPLATE,
                 LEAD_ID=1,
                 TAGS=[{'TAG_NAME': 'lol'}],
                 CONVERTED_ORGANIZATION_ID=1,
                 CONVERTED_OPPORTUNITY_ID=1,
                 CONVERTED_CONTACT_ID=1,
                 TITLE='LEAD1'),
            dict(LEAD_TEMPLATE,
                 LEAD_ID=2,
                 TAGS=[{'TAG_NAME': 'lol2'}],
                 CONVERTED_ORGANIZATION_ID=2,
                 CONVERTED_OPPORTUNITY_ID=2,
                 CONVERTED_CONTACT_ID=2,
                 TITLE='LEAD2'),
        ]
        # AND two corresponding contacts
        self.fake_insightly.get_response['/contacts/1'] = dict(
            CONTACT_TEMPLATE,
            CONTACT_ID=1,
            CUSTOMFIELDS=[]
        )
        self.fake_insightly.get_response['/contacts/2'] = dict(
            CONTACT_TEMPLATE,
            CONTACT_ID=2,
            CUSTOMFIELDS=[]
        )

        # WHEN fix_leads() is called
        insightly_automation.fix_leads()

        # THEN only one contact should be modified with new title
        insightly_automation.insightly_put.assert_called_once_with(
            '/contacts/2',
            (config.INSIGHTLY_API_KEY, ''),
            json=dict(
                CONTACT_TEMPLATE,
                CONTACT_ID=2,
                CUSTOMFIELDS=[{'CUSTOM_FIELD_ID': 'CONTACT_FIELD_1', 'FIELD_VALUE': 'LEAD2'}])
        )
