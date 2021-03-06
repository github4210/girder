#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
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

import os
import six

from tests import base
from girder import events
from girder.constants import ROOT_DIR
from girder.utility.model_importer import ModelImporter
from PIL import Image


def setUpModule():
    base.enabledPlugins.append('thumbnails')
    base.startServer()


def tearDownModule():
    base.stopServer()


class ThumbnailsTestCase(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        # Create some test documents with an item
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)

        user = {
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword',
            'admin': False
        }
        self.user = self.model('user').createUser(**user)

        folders = self.model('folder').childFolders(
            parent=self.admin, parentType='user', user=self.admin)
        for folder in folders:
            if folder['public'] is True:
                self.publicFolder = folder
            else:
                self.privateFolder = folder

        events.unbind('thumbnails.create', 'test')

    def testThumbnailCreation(self):
        path = os.path.join(ROOT_DIR, 'clients', 'web', 'src', 'assets', 'Girder_Mark.png')
        with open(path, 'rb') as file:
            data = file.read()

        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.png',
                'size': len(data)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'test.png', data)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files, user=self.admin)
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        params = {
            'fileId': fileId,
            'width': 64,
            'attachToId': str(self.admin['_id']),
            'attachToType': 'user'
        }

        # We shouldn't be able to add thumbnails without write access to the
        # target resource.
        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 403)

        # Should complain if we don't pass a width or a height
        del params['width']
        params['attachToId'] = str(self.user['_id'])

        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You must specify a valid width,'
                         ' height, or both.')

        # Set a width, we should now correctly have a thumbnail
        params['width'] = 64
        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        job = resp.json

        from girder.plugins.jobs.constants import JobStatus
        self.assertEqual(job['status'], JobStatus.SUCCESS)

        self.user = self.model('user').load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 1)
        thumbnailId = self.user['_thumbnails'][0]

        resp = self.request('/file/%s/download' % str(thumbnailId),
                            isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(six.BytesIO(data))
        self.assertEqual(image.size, (64, 64))

        # Delete the thumbnail, it should be removed from the user thumb list
        resp = self.request('/file/%s' % str(thumbnailId), method='DELETE',
                            user=self.user)
        self.assertStatusOk(resp)

        self.assertEqual(self.model('file').load(thumbnailId), None)
        self.user = self.model('user').load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 0)

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)
        self.publicFolder = self.model('folder').load(
            self.publicFolder['_id'], force=True)
        self.assertEqual(len(self.publicFolder['_thumbnails']), 1)

        thumbnailId = self.publicFolder['_thumbnails'][0]

        resp = self.request('/file/%s/download' % str(thumbnailId),
                            isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(six.BytesIO(data))
        self.assertEqual(image.size, (64, 32))

        # Deleting the public folder should delete the thumbnail as well
        self.model('folder').remove(self.publicFolder)
        self.assertEqual(self.model('file').load(thumbnailId), None)

    def testDicomThumbnailCreation(self):
        path = os.path.join(ROOT_DIR, 'plugins', 'thumbnails', 'plugin_tests', 'data',
                            'sample_dicom.dcm')
        with open(path, 'rb') as file:
            data = file.read()

        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.dcm',
                'size': len(data)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'test.dcm', data)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files, user=self.admin)
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        params = {
            'fileId': fileId,
            'width': 64,
            'attachToId': str(self.admin['_id']),
            'attachToType': 'user'
        }

        # We shouldn't be able to add thumbnails without write access to the
        # target resource.
        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 403)

        # Should complain if we don't pass a width or a height
        del params['width']
        params['attachToId'] = str(self.user['_id'])

        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatus(resp, 400)
        self.assertEqual(resp.json['message'], 'You must specify a valid width,'
                         ' height, or both.')

        # Set a width, we should now correctly have a thumbnail
        params['width'] = 64
        resp = self.request(
            path='/thumbnail', method='POST', user=self.user, params=params)
        self.assertStatusOk(resp)
        job = resp.json

        from girder.plugins.jobs.constants import JobStatus
        self.assertEqual(job['status'], JobStatus.SUCCESS)

        self.user = self.model('user').load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 1)
        thumbnailId = self.user['_thumbnails'][0]

        resp = self.request('/file/%s/download' % str(thumbnailId),
                            isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(six.BytesIO(data))
        self.assertEqual(image.size, (64, 64))

        # Delete the thumbnail, it should be removed from the user thumb list
        resp = self.request('/file/%s' % str(thumbnailId), method='DELETE',
                            user=self.user)
        self.assertStatusOk(resp)

        self.assertEqual(self.model('file').load(thumbnailId), None)
        self.user = self.model('user').load(self.user['_id'], force=True)
        self.assertEqual(len(self.user['_thumbnails']), 0)

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)
        self.publicFolder = self.model('folder').load(
            self.publicFolder['_id'], force=True)
        self.assertEqual(len(self.publicFolder['_thumbnails']), 1)

        thumbnailId = self.publicFolder['_thumbnails'][0]

        resp = self.request('/file/%s/download' % str(thumbnailId),
                            isJson=False)
        data = self.getBody(resp, text=False)
        image = Image.open(six.BytesIO(data))
        self.assertEqual(image.size, (64, 32))

        # Deleting the public folder should delete the thumbnail as well
        self.model('folder').remove(self.publicFolder)
        self.assertEqual(self.model('file').load(thumbnailId), None)

    def testCreateThumbnailOverride(self):
        def override(event):
            # Override thumbnail creation -- just grab the first 4 bytes
            self.assertIn('file', event.info)

            streamFn = event.info['streamFn']
            stream = streamFn()
            contents = b''.join(stream())

            uploadModel = ModelImporter.model('upload')

            upload = uploadModel.createUpload(
                user=self.admin, name='magic', parentType=None, parent=None,
                size=4)

            thumbnail = uploadModel.handleChunk(upload, contents[:4])

            event.addResponse({
                'file': thumbnail
            })
            event.preventDefault()

        events.bind('thumbnails.create', 'test', override)
        path = os.path.join(ROOT_DIR, 'clients', 'web', 'src', 'assets', 'Girder_Mark.png')
        with open(path, 'rb') as file:
            data = file.read()

        # Upload the Girder logo to the admin's public folder
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': 'test.png',
                'size': len(data)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', 'test.png', data)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files, user=self.admin)
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        fileId = resp.json['_id']

        # Attach a thumbnail to the admin's public folder
        resp = self.request(
            path='/thumbnail', method='POST', user=self.admin, params={
                'width': 64,
                'height': 32,
                'crop': True,
                'attachToId': str(self.publicFolder['_id']),
                'attachToType': 'folder',
                'fileId': fileId
            })
        self.assertStatusOk(resp)

        # Download the new thumbnail
        folder = self.model('folder').load(self.publicFolder['_id'], force=True)
        self.assertEqual(len(folder['_thumbnails']), 1)
        thumbnail = self.model('file').load(folder['_thumbnails'][0],
                                            force=True)

        self.assertEqual(thumbnail['attachedToType'], 'folder')
        self.assertEqual(thumbnail['attachedToId'], folder['_id'])

        # Its contents should be the PNG magic number
        stream = self.model('file').download(thumbnail, headers=False)
        self.assertEqual(b'\x89PNG', b''.join(stream()))
