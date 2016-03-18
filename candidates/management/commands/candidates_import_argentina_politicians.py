#!/usr/bin/python
# -*- coding: utf-8 -*-

#from __future__ import print_function, unicode_literals

import csv, time

from django.core.management.base import BaseCommand
#from django.db import transaction

from popolo.models import Organization, Area, Post, Person, Membership
from candidates.models.popolo_extra import OrganizationExtra

class Command(BaseCommand):
    help = "Imports politicians from 'estructura-organica.csv' to DB (popolo_organization)"

    #executivePowerCache --> <Organization>
    executivePowerCache = None
    def prepareExecutivePowerCache(self):
        self.executivePowerCache = Organization.objects.get(name='Poder Ejecutivo')

    #argentinaCache --> <Area>
    argentinaCache = None
    def prepareArgentinaCache(self):
        self.argentinaCache = Area.objects.get(name='Argentina')

    def prepareCaches(self):
        self.prepareExecutivePowerCache()
        self.prepareArgentinaCache()

    def createMermbership(self, date, role, organizationId, personId, postId):
        membership = Membership(
            created_at = date,
            updated_at = date,
            label = role,
            role = role,
            organization_id = organizationId,
            person_id = personId,
            post_id = postId,
            area_id = self.argentinaCache.id
        )
        membership.save()

    def createPerson(self, date, name, lastName, mail):
        person = Person(
            created_at = date,
            updated_at = date,
            name = name.decode('utf8'),
            family_name = lastName.decode('utf8'),
            given_name = '',
            additional_name = '',
            honorific_prefix = '',
            honorific_suffix = '',
            patronymic_name = '',
            sort_name = '',
            email = mail,
            gender = '',
            birth_date = '',
            death_date = '',
            summary = '',
            biography = '',
        )
        person.save()
        return person

    def createPost(self, date, role, organizationId):
        post = Post(
            created_at = date,
            updated_at = date,
            label = role,
            role = role,
            organization_id = organizationId,
            area_id = self.argentinaCache.id
        )
        post.save()
        return post

    def createOrganization(self, date, name, parentId):
        organization = Organization(
            created_at = date,
            updated_at = date,
            name = name,
            classification = 'goverment',
            parent_id = parentId,
            description = '',
            summary = '',
            area_id = self.argentinaCache.id
        )
        organization.save()
        
        organizationOextra = OrganizationExtra(
            register = '',
            base_id = organization.id,
            slug = 'goverment:' + str(organization.id)
        )
        organizationOextra.save()
        
        return organization

    def fetchAllPositions(self):
        print ("Inserting Organizations...\n")
        with open('estructura-organica.csv') as f:
            data = [tuple(line) for line in csv.reader(f)]

        date = time.strftime('%Y-%m-%d %H:%M:%S')
        storedOrganizationsCache = {}
        
        for row in data[1:]:
            organizationName = row[1]
            parentName = row[2].lower()
            
            if parentName in storedOrganizationsCache:
                parentId = storedOrganizationsCache[parentName]
            else:
                parentId = self.executivePowerCache.id

            organization = self.createOrganization(date, organizationName, parentId)
            storedOrganizationsCache[organization.name.lower()] = organization.id

            role = row[5]
            post = self.createPost(date, role, organization.id)

            personName = row[8]
            if personName:
                personLastName = row[7]
                mail = row[19]
                if mail:
                    mail = [x.strip() for x in mail.split(',')][0]
                else:
                    mail = ''
                person = self.createPerson(date, personName, personLastName, mail)

                self.createMermbership(date, role, organization.id, person.id, post.id)

    def handle(self, *args, **options):
        self.prepareCaches()
        self.fetchAllPositions()
