from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from popolo.models import Person

from compat import python_2_unicode_compatible


class SimplePopoloField(models.Model):
    VALID_FIELDS = (
        ('name', _('Name')),
        ('family_name', _('Family Name')),
        ('given_name', _('Given Name')),
        ('additional_name', _('Additional Name')),
        ('honorific_prefix', _('Honorific Prefix')),
        ('honorific_suffix', _('Honorific Suffix')),
        ('patronymic_name', _('Patronymic Name')),
        ('sort_name', _('Sort Name')),
        ('email', _('Email')),
        ('gender', _('Gender')),
        ('birth_date', _('Birth Date')),
        ('death_date', _('Death Date')),
        ('summary', _('Summary')),
        ('biography', _('Biography')),
        ('national_identity', _('National Identity')),
    )

    name = models.CharField(
        choices=VALID_FIELDS,
        max_length=256
    )
    label = models.CharField(max_length=256)
    required = models.BooleanField(default=False)
    info_type_key = models.CharField(
        choices=(
            ('text', _('Text Field')),
            ('email', _('Email Field')),
        ),
        max_length=256
    )
    order = models.IntegerField(blank=True)


@python_2_unicode_compatible
class ExtraField(models.Model):

    LINE = 'line'
    LONGER_TEXT = 'longer-text'
    URL = 'url'
    YESNO = 'yesno'

    FIELD_TYPES = (
        (LINE, 'A single line of text'),
        (LONGER_TEXT, 'One or more paragraphs of text'),
        (URL, 'A URL'),
        (YESNO, 'A Yes/No/Don\'t know dropdown')
    )

    key = models.CharField(max_length=256)
    type = models.CharField(
        max_length=64,
        choices=FIELD_TYPES,
    )
    label = models.CharField(max_length=1024)

    def __str__(self):
        return self.key


class PersonExtraFieldValue(models.Model):

    class Meta:
        unique_together = (('person', 'field'))

    person = models.ForeignKey(Person, related_name='extra_field_values')
    field = models.ForeignKey(ExtraField)
    value = models.TextField(blank=True)
