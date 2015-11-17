#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2014 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import cherrypy
import os
import six
import smtplib

from email.mime.text import MIMEText
from mako.lookup import TemplateLookup
from girder import events
from girder import logger
from girder.constants import SettingKey, PACKAGE_DIR
from .model_importer import ModelImporter


def getEmailUrlPrefix():
    """
    Return the URL prefix for links back to the server. This is the link to the
    server root, so Girder-level path information and any query parameters or
    fragment value should be appended to this value.
    """
    host = ModelImporter.model('setting').get(SettingKey.EMAIL_HOST, '')
    if not host:
        host = '://'.join((cherrypy.request.scheme,
                           cherrypy.request.local.name))
        if cherrypy.request.local.port != 80:
            host += ':{}'.format(cherrypy.request.local.port)

    return host


def renderTemplate(name, params=None):
    """
    Renders one of the HTML mail templates located in girder/mail_templates.

    :param name: The name of the file inside girder/mail_templates to render.
    :param params: The parameters to pass when rendering the template.
    :type params: dict
    :returns: The rendered template as a string of HTML.
    """
    if not params:
        params = {}

    if 'host' not in params:
        params['host'] = getEmailUrlPrefix()

    template = _templateLookup.get_template(name)
    return template.render(**params)


def sendEmail(to=None, subject=None, text=None, toAdmins=False):
    """
    Send an email. This builds the appropriate email object and then triggers
    an asynchronous event to send the email (handled in _sendmail).

    :param to: The recipient's email address, or a list of addresses.
    :type to: str, list/tuple, or None
    :param subject: The subject line of the email.
    :type subject: str
    :param text: The body of the email.
    :type text: str
    :param toAdmins: To send an email to all site administrators, set this
        to True, which will override any "to" argument that was passed.
    :type toAdmins: bool
    """
    if toAdmins:
        to = [u['email'] for u in ModelImporter.model('user').getAdmins()]
    elif isinstance(to, six.string_types):
        to = (to,)

    if not isinstance(to, (list, tuple)):
        raise Exception('You must specify a "to" address or list of addresses '
                        'or set toAdmins=True when calling sendEmail.')

    msg = MIMEText(text, 'html')
    msg['Subject'] = subject or '[no subject]'
    msg['To'] = ', '.join(to)
    msg['From'] = ModelImporter.model('setting').get(
        SettingKey.EMAIL_FROM_ADDRESS, 'no-reply@girder.org')

    events.daemon.trigger('_sendmail', info={
        'message': msg,
        'recipients': to
    })


def addTemplateDirectory(dir, prepend=False):
    """
    Adds a directory to the search path for mail templates. This is useful
    for plugins that have their own set of mail templates.

    :param dir: The directory to add to the template lookup path.
    :type dir: str
    :param prepend: If True, adds this directory at the beginning of the path so
        that it will override any existing templates with the same name.
        Otherwise appends to the end of the lookup path.
    :type prepend: bool
    """
    idx = 0 if prepend else len(_templateLookup.directories)
    _templateLookup.directories.insert(idx, dir)


class _SMTPConnection(object):
    def __init__(self, host, port=None, encryption=None,
                 username=None, password=None):
        self.host = host
        self.port = port
        self.encryption = encryption
        self.username = username
        self.password = password

    def __enter__(self):
        if self.encryption == 'ssl':
            self.connection = smtplib.SMTP_SSL(self.host, self.port)
        else:
            self.connection = smtplib.SMTP(self.host, self.port)
            if self.encryption == 'starttls':
                self.connection.starttls()
        if self.username and self.password:
            self.connection.login(self.username, self.password)
        return self

    def send(self, fromAddress, toAddresses, message):
        self.connection.sendmail(fromAddress, toAddresses, message)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.quit()


def _sendmail(event):
    msg = event.info['message']

    setting = ModelImporter.model('setting')
    smtp = _SMTPConnection(
        host=setting.get(SettingKey.SMTP_HOST, 'localhost'),
        port=setting.get(SettingKey.SMTP_PORT, None),
        encryption=setting.get(SettingKey.SMTP_ENCRYPTION, 'none'),
        username=setting.get(SettingKey.SMTP_USERNAME, None),
        password=setting.get(SettingKey.SMTP_PASSWORD, None),
    )

    logger.info('Sending email to %s through %s', msg['To'], smtp.host)

    with smtp:
        smtp.send(msg['From'], event.info['recipients'], msg.as_string())

    logger.info('Sent email to %s', msg['To'])


_templateDir = os.path.join(PACKAGE_DIR, 'mail_templates')
_templateLookup = TemplateLookup(directories=[_templateDir], collection_size=50)
events.bind('_sendmail', 'core.email', _sendmail)
