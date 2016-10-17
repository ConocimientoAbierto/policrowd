#!/usr/bin/python
# -*- coding: utf-8 -*-

#from __future__ import print_function, unicode_literals

import csv, time
from os.path import dirname, join

from django.core.management.base import BaseCommand
#from django.db import transaction

from popolo.models import Organization, Area, Post, Person, Membership
from candidates.models.popolo_extra import OrganizationExtra, PersonExtra

class Command(BaseCommand):
    help = "Imports politicians from 'estructura-organica.csv' to DB (popolo_organization)"

    #contadores
    areas, organizations, persons, posts, memberships = 0, 0, 0, 0, 0

    #argentinaCache --> <Area>
    argentinaCache = None
    def prepareArgentinaCache(self):
        area = Area.objects.get_or_create(name='Argentina')

        self.plusCounter(area[1], 'area')
        self.argentinaCache = area[0]

    #executivePowerCache --> <Organization>
    executivePowerCache = None
    def prepareExecutivePowerCache(self):
        executivePower = Organization.objects.get_or_create(name= 'Poder Ejecutivo', area_id= self.argentinaCache.id,
            defaults={
                'classification': 'poder'
            }
        )

        self.plusCounter(executivePower[1], 'organization')
        self.executivePowerCache = executivePower[0]

        #TODO This code just create two new powers but the never are used,
        # and the name it's not right
        Organization.objects.get_or_create(
            name = 'Poder Legislativo',
            area_id = self.argentinaCache.id,
            defaults = {
                'classification': 'poder'
            }
        )
        Organization.objects.get_or_create(name='Poder Judicial', area_id= self.argentinaCache.id,
            defaults={
                'classification': 'poder'
            }
        )

    def prepareCaches(self):
        self.prepareArgentinaCache()
        self.prepareExecutivePowerCache()

    def createMermbership(self, role, organizationId, personId, postId):
        membership = Membership.objects.get_or_create(
            person_id = personId,
            organization_id = organizationId,
            post_id = postId,
            area_id = self.argentinaCache.id,
            defaults = {
                'label': '',
                'role': '',
                'start_date': '2015-12-10',  # time.strftime('%Y-%m-%d'),
                'end_date': '2019-12-10'
            }
        )

        self.plusCounter(membership[1], 'membership')

    def createPerson(self, name, lastName, mail, honorPrefix):
        lastName = lastName.decode('utf8').title()
        name = name.decode('utf8').title()
        fullName = name + ' ' + lastName
        person = Person.objects.update_or_create(
            name = fullName,
            family_name = lastName,
            given_name = name,
            defaults = {
                'additional_name': '',
                'honorific_prefix': honorPrefix,
                'honorific_suffix': '',
                'patronymic_name': '',
                'sort_name': '',
                'email': mail,
                'gender': '',
                'birth_date': '',
                'death_date': '',
                'summary': '',
                'biography': '',
            }
        )

        if (person[1]):
            personExtra = PersonExtra(
                base_id = person[0].id,
                versions = '[]'
            )
            personExtra.save()

        self.plusCounter(person[1], 'person')
        return person[0]

    def createPost(self, role, organizationId):
        post = Post.objects.get_or_create(
            role = role,
            organization_id = organizationId,
            area_id = self.argentinaCache.id,
            label = role
        )

        self.plusCounter(post[1], 'post')
        return post[0]

    def createOrganization(self, name, parentId):
        organization = Organization.objects.get_or_create(
            name = name,
            area_id = self.argentinaCache.id,
            parent_id = parentId,
            defaults = {
                'classification': 'goverment',
            }
        )

        if (organization[1]):
            organizationExtra = OrganizationExtra(
                register = '',
                base_id = organization[0].id,
                slug = 'goverment:' + str(organization[0].id)
            )
            organizationExtra.save()

        self.plusCounter(organization[1], 'organization')
        return organization[0]

    def fetchAllPositions(self):
        print ("Inserting Organizations...\n")
        filename = 'estructura-organica.csv'
        csv_filename = join(
            dirname(__file__), '..', '..', 'data', filename
        )
        with open(csv_filename) as f:
            data = [tuple(line) for line in csv.reader(f)]

        storedOrganizationsCache = {}

        for row in data[1:]:
            organizationName = row[1]
            parentName = row[2].lower()

            if parentName in storedOrganizationsCache:
                parentId = storedOrganizationsCache[parentName]
            else:
                parentId = self.executivePowerCache.id

            organization = self.createOrganization(organizationName, parentId)
            storedOrganizationsCache[organization.name.lower()] = organization.id

            role = row[5]
            post = self.createPost(role, organization.id)

            personName = row[8] #old 8
            # personName = row[7] #old 8
            if personName:
                personLastName = row[7] # old 7
                # personLastName = row[8] # old 7
                mail = row[19] # old 19
                # mail = row[20] # old 19
                honorPrefix = row[6]
                if mail:
                    mail = [x.strip() for x in mail.split(',')][0]
                else:
                    mail = ''

                person = self.createPerson(personName, personLastName, mail, honorPrefix)

                self.createMermbership(role, organization.id, person.id, post.id)

    def plusCounter(self, plus, category):
        if plus:
            if category == 'area':
                self.areas = self.areas + 1
            elif category == 'organization':
                self.organizations = self.organizations + 1
            elif category == 'person':
                self.persons = self.persons + 1
            elif category == 'post':
                self.posts = self.posts + 1
            elif category == 'membership':
                self.memberships = self.memberships + 1

    def handle(self, *args, **options):
        self.prepareCaches()
        self.fetchAllPositions()
        print 'Nuevas areas: ', self.areas
        print 'Nuevas organizaciones: ', self.organizations
        print 'Nuevas peronas: ', self.persons
        print 'Nuevas puestos: ',  self.posts
        print 'Nuevas cargos: ',  self.memberships
