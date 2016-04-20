#!/usr/bin/python
# -*- coding: utf-8 -*-

#from __future__ import print_function, unicode_literals

import csv, time
from os.path import dirname, join

from django.core.management.base import BaseCommand
#from django.db import transaction

from candidates.models import AreaExtra
from elections.models import AreaType
from popolo.models import Area


class Command(BaseCommand):
    help = "Imports areas in 'ARG_adm2.csv' to DB (popolo_area)"

    #areaTypesCache --> { <name> : <id>}
    areaTypesCache = {}
    def prepareAreaTypesCache(self):
        AreaType.objects.get_or_create(name="NAT")
        AreaType.objects.get_or_create(name="PRV")
        AreaType.objects.get_or_create(name="MUN")
        areaTypes = AreaType.objects.only('name', 'id').all()

        for areaType in areaTypes:
            self.areaTypesCache[areaType.name] = areaType.id

    #provincesAreasCache --> { <name> : <id> }
    provincesAreasCache = {}
    def prepareCaches(self, date, data):
        self.prepareAreaTypesCache()

        argentinaQuery = Area.objects.get_or_create(name='Argentina', defaults={
            'created_at':date,
            'updated_at':date,
            'identifier':1,
            'classification':''
        })
        argentinaId = argentinaQuery[0].id
        argentinaWasCreated = argentinaQuery[1]

        if argentinaWasCreated:
            AreaExtra(base_id = argentinaId, type_id = self.areaTypesCache['NAT']).save()

        provinces = Area.objects.only('name', 'id').filter(parent_id=argentinaId)
        for area in provinces:
            self.provincesAreasCache[area.name] = area.id
        
        provTypeId = self.areaTypesCache['PRV']

        i = 2
        for row in data[1:]:
            provName = row[5]
            if not provName in self.provincesAreasCache:
                createdProvince = Area(
                    created_at = date,
                    updated_at = date,
                    name = provName,
                    parent_id = argentinaId,
                    identifier = i,
                    classification = ''
                )
                createdProvince.save()
                AreaExtra(base_id = createdProvince.id, type_id = provTypeId).save()

                self.provincesAreasCache[provName] = createdProvince.id
                i += 1

    def fetchAllAreas(self):
        print ("Inserting Areas...\n")
        filename = 'ARG_adm2.csv'
        csv_filename = join(
            dirname(__file__), '..', '..', 'data', filename
        )        
        with open(csv_filename) as f:
            data = [tuple(line) for line in csv.reader(f)]

        identifierBase = 100 # Para que no se pisen con los ya cargados. Esto va a cambiar cuando usemos los ids de OSM
        date = time.strftime('%Y-%m-%d %H:%M:%S')

        self.prepareCaches(date, data)
        areaTypeId = self.areaTypesCache['MUN']
        
        for row in data[1:]:
            identifier = str(identifierBase + int(row[0]))
            parentAreaName = row[5]
            parentId = self.provincesAreasCache[parentAreaName]
            areaName = row[7]
            area = Area(
                parent_id = parentId,
                name = areaName,
                created_at = date,
                updated_at = date,
                identifier = identifier,
                classification = ''
            )
            area.save()

            areaExtra = AreaExtra(
                base_id = area.id,
                type_id = areaTypeId
            )
            areaExtra.save()
        
        
    def handle(self, *args, **options):
        self.fetchAllAreas()
