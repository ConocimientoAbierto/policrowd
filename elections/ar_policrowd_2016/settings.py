# -*- coding: utf-8 -*-

from __future__ import unicode_literals
import os

MAPIT_BASE_URL = 'http://argentina.mapit.staging.mysociety.org/'

SITE_OWNER = 'Fundación Conocimiento Abierto'
COPYRIGHT_HOLDER = 'Fundación Conocimiento Abierto'


EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [os.path.join('~/Software/yournextrepresentative/candidates', 'templates')],
    'OPTIONS': {
        'loaders': [
            ('django.template.loaders.cached.Loader', [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]),
        ],
    },
}]
