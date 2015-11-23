# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import errno
import hashlib
import json
import os
from os.path import join, exists, dirname
import re
import requests
import shutil
from datetime import date, timedelta
from dateutil.parser import parse

from PIL import Image as PillowImage

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.management.color import no_style
from django.db import connection, migrations

from popolo.importers.popit import PopItImporter, show_data_on_error

PILLOW_FORMAT_EXTENSIONS = {
    'JPEG': 'jpg',
    'PNG': 'png',
    'GIF': 'gif',
    'BMP': 'bmp',
}

CACHE_DIRECTORY = join(dirname(__file__), '.download-cache')

def get_url_cached(url):
    try:
        os.makedirs(CACHE_DIRECTORY)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    filename = join(CACHE_DIRECTORY, hashlib.md5(url).hexdigest())
    if exists(filename):
        return filename
    else:
        print "\nDownloading {0} ...".format(url)
        with open(filename, 'wb') as f:
            r = requests.get(url, stream=True)
            r.raise_for_status()
            shutil.copyfileobj(r.raw, f)
        print "done"
    return filename

class YNRPopItImporter(PopItImporter):

    person_id_to_json_data = {}

    def __init__(self, apps, schema_editor):
        self.apps = apps
        self.schema_editor = schema_editor
        self.image_storage = FileSystemStorage()
        Election = self.get_model_class('elections', 'Election')
        self.election_cache = {
            e.slug: e for e in Election.objects.all()
        }

    def get_model_class(self, app_label, model_name):
        return self.apps.get_model(app_label, model_name)

    def get_images_for_object(self, images_data, django_extra_object):
        ContentType = self.get_model_class('contenttypes', 'ContentType')
        person_extra_content_type = ContentType.objects.get_for_model(django_extra_object)

        # Now download and import all the images:
        Image = self.get_model_class('images', 'Image')
        first_image = True
        for image_data in images_data:
            with show_data_on_error('image_data', image_data):
                url = image_data['url']
                try:
                    image_filename = get_url_cached(url)
                except requests.exceptions.HTTPError as e:
                    msg = "Ignoring image URL {url}, with status code {status}"
                    print msg.format(
                        url=url,
                        status=e.response.status_code
                    )
                    continue
                with open(image_filename, 'rb') as f:
                    try:
                        pillow_image = PillowImage.open(f)
                    except IOError as e:
                        if 'cannot identify image file' in unicode(e):
                            print "Ignoring a non-image file {0}".format(
                                image_filename
                            )
                            continue
                        raise
                    extension = PILLOW_FORMAT_EXTENSIONS[pillow_image.format]
                suggested_filename = join(
                    'images', image_data['id'] + '.' + extension
                )
                with open(image_filename, 'rb') as f:
                    storage_filename = self.image_storage.save(
                        suggested_filename, f
                    )
                image_uploaded_by = image_data.get('uploaded_by_user', '')
                image_notes = image_data.get('notes', '')
                source = 'Uploaded by {uploaded_by}: {notes}'.format(
                    uploaded_by=image_uploaded_by,
                    notes=image_notes,
                )
                Image.objects.create(
                    image=storage_filename,
                    source=source,
                    is_primary=first_image,
                    object_id=django_extra_object.id,
                    content_type_id=person_extra_content_type.id
                )
            if first_image:
                first_image = False

    def update_person(self, person_data):
        new_person_data = person_data.copy()
        # There are quite a lot of summary fields in PopIt that are
        # way longer than 1024 characters.
        new_person_data['summary'] = (person_data.get('summary') or '')[:1024]
        # Surprisingly, quite a lot of PopIt email addresses have
        # extraneous whitespace in them, so strip any out to avoid
        # the 'Enter a valid email address' ValidationError on saving:
        email = person_data.get('email') or None
        if email:
            email = re.sub(r'\s*', '', email)
        new_person_data['email'] = email
        # We would like people to have the same ID as they did in
        # PopIt (where the person IDs were just stringified
        # integers). So create a minimal person with the right ID and
        # an identifier to that the method we're overriding will
        # notice that it exists.  n.b. this means we have to reset the
        # person id sequence at the end of import_from_popit
        Person = self.get_popolo_model_class('Person')
        minimal_person = Person.objects.create(
            id=int(person_data['id']),
            name=person_data['name'],
        )
        self.create_identifier('person', person_data['id'], minimal_person)
        # Now the superclass method should find and update that person.
        person_id, person = super(YNRPopItImporter, self).update_person(
            new_person_data
        )

        self.person_id_to_json_data[person_data['id']] = new_person_data

        # Create the extra person object:
        PersonExtra = self.get_model_class('candidates', 'PersonExtra')
        extra = PersonExtra.objects.create(
            base=person,
            versions=json.dumps(new_person_data['versions'])
        )

        self.get_images_for_object(person_data['images'], extra)

        return person_id, person

    def update_organization(self, org_data, area):
        org_id, org = super(YNRPopItImporter, self).update_organization(
            org_data, area
        )

        # Create the extra organization object:
        OrganizationExtra = self.get_model_class('candidates', 'OrganizationExtra')
        register = org_data.get('register') or ''
        extra = OrganizationExtra.objects.create(
            base=org,
            slug=org_data['id'],
            register=register,
        )

        self.get_images_for_object(org_data['images'], extra)

        return org_id, org

    def update_post(self, post_data, area, org_id_to_django_object):
        post_id, post = super(YNRPopItImporter, self).update_post(post_data, area, org_id_to_django_object)

        PostExtra = self.get_model_class('candidates', 'PostExtra')
        post_extra, created = PostExtra.objects.get_or_create(base=post, slug=post_data['id'])
        post_extra.candidates_locked = post_data.get('candidates_locked', False)
        post_extra.save()

        for election_slug in post_data['elections']:
            post_extra.elections.add(self.election_cache[election_slug])

        return post_id, post

    def update_membership(
        self,
        membership_data,
        area,
        org_id_to_django_object,
        post_id_to_django_object,
        person_id_to_django_object,
    ):
        membership_id, membership = super(YNRPopItImporter, self).update_membership(
            membership_data,
            area,
            org_id_to_django_object,
            post_id_to_django_object,
            person_id_to_django_object,
        )
        Election = self.get_model_class('elections', 'Election')

        election_slug = membership_data.get('election', None)
        # This is an unfortunate fixup to have to do. It seems that
        # the scripts that we used to make sure that all memberships
        # representing candidacies had an 'election' property didn't
        # work consistently; lots of candidacies are missing it.  So,
        # if it looks as if the membership is a candidacy and it's
        # missing its election property, set it. This inference
        # wouldn't work in general but should work for all the data in
        # the known YNR instances based on PopIt:
        candidacy = membership.role.lower() not in (None, '', 'member')
        if (not election_slug) and candidacy and membership.post:
            matching_elections = list(Election.objects.filter(
                for_post_role=membership.post.role,
                candidate_membership_role=membership.role,
                election_date__gte=membership.start_date,
                election_date__lte=membership.end_date,
                organization_name=membership.post.organization.name,
            ))
            # If there's exactly one matching election, that's ideal:
            if len(matching_elections) == 1:
                election_slug = matching_elections[0].slug
            # If we hit the ambiguity between the two types of
            # Parlamentario Mercosur, there's a special case for that:
            elif len(matching_elections) == 2 and \
                    (membership.post.role == 'Parlamentario Mercosur'):
                if membership.post.slug == 'pmeu':
                    election_slug = 'parlamentarios-mercosur-unico-paso-2015'
                else:
                    election_slug = 'parlamentarios-mercosur-regional-paso-2015'
            else:
                raise Exception("Election missing on membership, and no unique matching election found")
        elif not election_slug and membership.post is not None:
            day_before_membership = parse(membership.start_date) - timedelta(days=1)
            matching_elections = list(Election.objects.filter(
                for_post_role=membership.post.role,
                organization_name=membership.organization.name,
                election_date=day_before_membership,
            ))
            if len(matching_elections) == 1:
                election_slug = matching_elections[0].slug
        if election_slug is not None:
            election = Election.objects.get(slug=election_slug)

            if membership.role == election.candidate_membership_role or \
                membership.organization.name == election.organization_name:
                MembershipExtra = self.get_model_class('candidates', 'MembershipExtra')
                me, created = MembershipExtra.objects.get_or_create(
                    base=membership,
                    election=election
                )

                person_data = self.person_id_to_json_data[membership_data['person_id']]
                party = person_data['party_memberships'].get(election.slug)
                if party is not None:
                    membership.on_behalf_of = org_id_to_django_object[party['id']]
                    membership.save()

                party_list_position = membership_data.get('party_list_position', None)
                if party_list_position is not None:
                    if me:
                        me.party_list_position = party_list_position
                        me.save()

                if membership.organization is not None and \
                    membership.organization.name == election.organization_name:
                    if me:
                        me.elected = True
                        me.save()



        start_date = membership_data.get('start_date', None)
        end_date = membership_data.get('end_date', None)

        if start_date is not None:
            membership.start_date = start_date
        if end_date is not None:
            membership.end_date = end_date

        membership.save()
        return membership_id, membership

    def make_contact_detail_dict(self, contact_detail_data):
        new_contact_detail_data = contact_detail_data.copy()
        # There are some contact types that are used in PopIt that are
        # longer than 12 characters...
        new_contact_detail_data['type'] = contact_detail_data['type'][:12]
        return super(YNRPopItImporter, self).make_contact_detail_dict(new_contact_detail_data)

    def make_link_dict(self, link_data):
        new_link_data = link_data.copy()
        # There are some really long URLs in PopIt, which exceed the
        # 200 character limit in django-popolo.
        new_link_data['url'] = new_link_data['url'][:200]
        return super(YNRPopItImporter, self).make_link_dict(new_link_data)


PARTY_SETS_BY_ELECTION_APP = {
    'uk_general_election_2015': [
        {'slug': 'gb', 'name': 'Great Britain'},
        {'slug': 'ni', 'name': 'Northern Ireland'},
    ],
    'st_paul_municipal_2015': [
        {'slug': 'st-paul', 'name': 'Saint Paul, Minnesota'},
    ],
    'ar_elections_2015': [
        {'slug': u'jujuy', 'name': u'Jujuy'},
        {'slug': u'la-rioja', 'name': u'La Rioja'},
        {'slug': u'catamarca', 'name': u'Catamarca'},
        {'slug': u'salta', 'name': u'Salta'},
        {'slug': u'nacional', 'name': u'Nacional'},
        {'slug': u'chaco', 'name': u'Chaco'},
        {'slug': u'mendoza', 'name': u'Mendoza'},
        {'slug': u'chubut', 'name': u'Chubut'},
        {'slug': u'capital-federal', 'name': u'Capital Federal'},
        {'slug': u'neuquen', 'name': u'Neuqu\xe9n'},
        {'slug': u'san-juan', 'name': u'San Juan'},
        {'slug': u'corrientes', 'name': u'Corrientes'},
        {'slug': u'la-pampa', 'name': u'La Pampa'},
        {'slug': u'formosa', 'name': u'Formosa'},
        {'slug': u'misiones', 'name': u'Misiones'},
        {'slug': u'cordoba', 'name': u'C\xf3rdoba'},
        {'slug': u'santiago-del-estero', 'name': u'Santiago Del Estero'},
        {'slug': u'san-luis', 'name': u'San Luis'},
        {'slug': u'buenos-aires', 'name': u'Buenos Aires'},
        {'slug': u'santa-cruz', 'name': u'Santa Cruz'},
        {'slug': u'rio-negro', 'name': u'R\xedo Negro'},
        {'slug': u'santa-fe', 'name': u'Santa Fe'},
        {'slug': u'tucuman', 'name': u'Tucum\xe1n'},
        {'slug': u'tierra-del-fuego', 'name': u'Tierra del Fuego'},
        {'slug': u'entre-rios', 'name': u'Entre R\xedos'}
    ],
    'bf_elections_2015': [
        {'slug': 'national', 'name': 'National'},
    ],
}

ELECTION_APPS_WITH_EXISTING_DATA = (
    'ar_elections_2015',
    'bf_elections_2015',
    'st_paul_municipal_2015',
    'uk_general_election_2015',
)

def import_from_popit(apps, schema_editor):
    if settings.ELECTION_APP not in ELECTION_APPS_WITH_EXISTING_DATA:
        return
    importer = YNRPopItImporter(apps, schema_editor)
    url = 'http://{instance}.{hostname}:{port}/api/v0.1/export.json'.format(
        instance=settings.POPIT_INSTANCE,
        hostname=settings.POPIT_HOSTNAME,
        port=settings.POPIT_PORT,
    )
    export_filename = get_url_cached(url)
    importer.import_from_export_json(export_filename)
    # Now reset the database sequence for popolo_person's id field,
    # since we've specified the id when creating each person.
    Person = apps.get_model('popolo', 'person')
    reset_sql_list = connection.ops.sequence_reset_sql(
        no_style(), [Person]
    )
    if reset_sql_list:
        cursor = connection.cursor()
        for reset_sql in reset_sql_list:
            print "Running reset SQL:", reset_sql
            cursor.execute(reset_sql)
    # Now create the party sets for this country:
    party_set_from_slug = {}
    party_set_from_name = {}
    for party_set_data in PARTY_SETS_BY_ELECTION_APP.get(
            settings.ELECTION_APP, []
    ):
        PartySet = apps.get_model('candidates', 'partyset')
        party_set = PartySet.objects.create(**party_set_data)
        party_set_from_slug[party_set_data['slug']] = party_set
        party_set_from_name[party_set_data['name']] = party_set
    # For Argentina, we need the original party JSON to decide on the
    # party sets.
    if settings.ELECTION_APP == 'ar_elections_2015':
        ar_party_id_to_party_sets = {}
        ar_filename = join(
            dirname(__file__), '..', '..', 'elections', 'ar_elections_2015',
            'data', 'all-parties-from-popit.json'
        )
        with open(ar_filename) as f:
            ar_all_party_data = json.load(f)
            for party_data in ar_all_party_data:
                territory = party_data.get('territory')
                if territory:
                    party_set = party_set_from_name[territory]
                    ar_party_id_to_party_sets[party_data['id']] = \
                        [party_set]
                else:
                    ar_party_id_to_party_sets[party_data['id']] = \
                        party_set_from_name.values()

    # And add each party to a party set:
    Organization = apps.get_model('popolo', 'organization')
    for party in Organization.objects.filter(
            classification='Party',
    ).prefetch_related('extra'):
        if settings.ELECTION_APP == 'bf_elections_2015':
            party.party_sets.add(party_set_from_slug['national'])
        elif settings.ELECTION_APP == 'st_paul_municipal_2015':
            party.party_sets.add(party_set_from_slug['st-paul'])
        elif settings.ELECTION_APP == 'uk_general_election_2015':
            register = party.extra.register
            if register == 'Great Britain':
                party.party_sets.add(party_set_from_slug['gb'])
            elif register == 'Northern Ireland':
                party.party_sets.add(party_set_from_slug['ni'])
            elif register:
                raise Exception("Unknown register {0}".format(register))
        elif settings.ELECTION_APP == 'ar_elections_2015':
            party_sets = ar_party_id_to_party_sets[party.extra.slug]
            party.party_sets.add(*party_sets)


class Migration(migrations.Migration):

    dependencies = [
        ('candidates', '0008_membershipextra_organizationextra_personextra_postextra'),
        ('images', '0001_initial'),
        ('popolo', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            import_from_popit,
            lambda apps, schema_editor: None
        ),
    ]
