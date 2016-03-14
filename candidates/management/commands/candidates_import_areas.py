#!/usr/bin/python
# -*- coding: utf-8 -*-

#from __future__ import print_function, unicode_literals

import csv, time

from django.core.management.base import BaseCommand
#from django.db import transaction

from candidates.models import AreaExtra
from elections.models import AreaType
from popolo.models import Area


class Command(BaseCommand):
    help = "Imports areas in ARG_adm2.csv to Data Base (popolo_area)"

    areaDifferencesMap = {
        'Buenos Aires': 'BUENOS AIRES',
        'Catamarca': 'CATAMARCA',
        'Chaco': 'CHACO',
        'Chubut': 'CHUBUT',
        'Ciudad de Buenos Aires': 'CIUDAD AUTONOMA DE BUENOS AIRES',
        'Córdoba' : 'CORDOBA',
        'Corrientes': 'CORRIENTES',
        'Entre Ríos': 'ENTRE RIOS',
        'Formosa': 'FORMOSA',
        'Jujuy': 'JUJUY',
        'La Pampa': 'LA PAMPA',
        'La Rioja': 'LA RIOJA',
        'Mendoza': 'MENDOZA',
        'Misiones': 'MISIONES',
        'Neuquén': 'NEUQUEN',
        'Río Negro': 'RIO NEGRO',
        'Salta': 'SALTA',
        'San Juan': 'SAN JUAN',
        'San Luis': 'SAN LUIS',
        'Santa Cruz': 'SANTA CRUZ',
        'Santa Fe': 'SANTA FE',
        'Santiago del Estero': 'SANTIAGO DEL ESTERO',
        'Tierra del Fuego': 'TIERRA DEL FUEGO, ANTARTIDA E ISLAS DEL ATLANTICO SUR',
        'Tucumán': 'TUCUMAN'
    }

    #provincesAreasCache --> { <name> : <id> }
    provincesAreasCache = {}
    def prepareProvincesAreasCache(self):
        argentinaId = Area.objects.only('id').get(name='Argentina').id
        provinces = Area.objects.only('name', 'id').filter(parent_id=argentinaId)

        for area in provinces:
            self.provincesAreasCache[area.name] = area.id

    #areaTypesCache --> { <name> : <id>}
    areaTypesCache = {}
    def prepareAreaTypesCache(self):
        areaTypes = AreaType.objects.only('name', 'id').all()

        for areaType in areaTypes:
            self.areaTypesCache[areaType.name] = areaType.id

    def prepareCaches(self):
        self.prepareProvincesAreasCache()
        self.prepareAreaTypesCache()

    def fetchAllAreas(self):
        #print "Inserting Areas...\n"
        with open('ARG_adm2.csv') as f:
            data = [tuple(line) for line in csv.reader(f)]

        areaTypeId = self.areaTypesCache['MUN']

        print (self.areaDifferencesMap)
        
        identifierBase = 100 # Para que no se pisen con los ya cargados. Esto va a cambiar cuando usemos los ids de OSM
        date = time.strftime('%Y-%m-%d %H:%M:%S')
        
        for row in data[1:]:
            identifier = str(identifierBase + int(row[0]))
            parentAreaName = row[5]
            parentId = self.provincesAreasCache[self.areaDifferencesMap[parentAreaName]]
            areaName = row[7]
            #cur.execute("INSERT INTO popolo_area (parent_id,name,created_at,updated_at,identifier,classification) \
            #    VALUES(%s,%s,%s,%s,%s,%s)", (parentId, areaName, date, date, identifier, '')
            #)
            area = Area(
                parent_id = parentId,
                name = areaName,
                created_at = date,
                updated_at = date,
                identifier = identifier,
                classification = ''
            )
            area.save()

            #cur.execute("INSERT INTO candidates_areaextra (base_id,type_id) VALUES(%s,%s)", (cur.fetchone()[0], areaTypeId))
            areaExtra = AreaExtra(
                base_id = area.id,
                type_id = areaTypeId
            )
            areaExtra.save()
        
        
    def handle(self, *args, **options):
        self.prepareCaches()
        self.fetchAllAreas()
