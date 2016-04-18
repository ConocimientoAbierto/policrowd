# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import re

from django.db.models import Prefetch
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponseBadRequest
from django.views.generic import TemplateView
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404

from candidates.models import AreaExtra, MembershipExtra
from candidates.models.auth import get_edits_allowed

from elections.models import AreaType, Election

from popolo import models as pmodels

from ..forms import NewPersonForm
from .helpers import split_candidacies, group_candidates_by_party

class AreasView(TemplateView):
    template_name = 'candidates/areas.html'

    def get(self, request, *args, **kwargs):
        self.types_and_areas = []
        for type_and_area in kwargs['type_and_area_ids'].split(','):
            m = re.search(r'^([A-Z0-9]+?)-([-a-zA-Z0-9\:_]+)$', type_and_area)
            if not m:
                message = _("Malformed type and area: '{0}'")
                return HttpResponseBadRequest(message.format(type_and_area))
            self.types_and_areas.append(m.groups())
        response = super(AreasView, self).get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = super(AreasView, self).get_context_data(**kwargs)
        all_area_names = set()
        context['posts'] = []
        any_area_found = False
        for area_type_code, area_id in self.types_and_areas:
            try:
                area_extra = AreaExtra.objects \
                    .select_related('base', 'type') \
                    .prefetch_related('base__posts') \
                    .get(base__identifier=area_id)
                any_area_found = True
            except AreaExtra.DoesNotExist:
                continue
            area = area_extra.base
            all_area_names.add(area.name)
            for post in area.posts.all():
                post_extra = post.extra
                try:
                    election = post_extra.elections.get(current=True)
                except Election.DoesNotExist:
                    continue
                locked = post_extra.candidates_locked
                extra_qs = MembershipExtra.objects.select_related('election')
                current_candidacies, _ = split_candidacies(
                    election,
                    post.memberships.prefetch_related(
                        Prefetch('extra', queryset=extra_qs)
                    ).select_related(
                        'person', 'person__extra', 'on_behalf_of',
                        'on_behalf_of__extra', 'organization'
                    ).all()
                )
                current_candidacies = group_candidates_by_party(
                    election,
                    current_candidacies,
                    party_list=election.party_lists_in_use,
                    max_people=election.default_party_list_members_to_show
                )
                context['posts'].append({
                    'election': election.slug,
                    'election_data': election,
                    'post_data': {
                        'id': post.extra.slug,
                        'label': post.label,
                    },
                    'candidates_locked': locked,
                    'candidate_list_edits_allowed':
                    get_edits_allowed(self.request.user, locked),
                    'candidacies': current_candidacies,
                    'add_candidate_form': NewPersonForm(
                        election=election.slug,
                        initial={
                            ('constituency_' + election.slug): post_extra.slug,
                            ('standing_' + election.slug): 'standing',
                        },
                        hidden_post_widget=True,
                    ),
                })
        if not any_area_found:
            raise Http404("No such areas found")
        context['all_area_names'] = ' — '.join(all_area_names)
        context['suppress_official_documents'] = True
        return context

class AreasOfTypeView(TemplateView):
    template_name = 'candidates/areas-of-type.html'

    def get_context_data(self, **kwargs):
        context = super(AreasOfTypeView, self).get_context_data(**kwargs)
        requested_area_type = kwargs['area_type']
        all_area_tuples = set(
            (area_type.name, election_data.area_generation)
            for election_data in Election.objects.current().by_date()
            for area_type in election_data.area_types.all()
            if area_type.name == requested_area_type
        )
        if not all_area_tuples:
            raise Http404(_("Area '{0}' not found").format(requested_area_type))
        if len(all_area_tuples) > 1:
            message = _("Multiple Area generations for type {area_type} found")
            raise Exception(message.format(area_type=requested_area_type))
        prefetch_qs = AreaExtra.objects.select_related('base').order_by('base__name')
        area_type = get_object_or_404(
            AreaType.objects \
                .prefetch_related(Prefetch('areas', queryset=prefetch_qs)),
            name=requested_area_type
        )
        areas = [
            (
                reverse(
                    'areas-view',
                    kwargs={
                        'type_and_area_ids': '{type}-{area_id}'.format(
                            type=requested_area_type,
                            area_id=area.base.identifier
                        ),
                        'ignored_slug': slugify(area.base.name)
                    }
                ),
                area.base.name,
                requested_area_type,
            )
            for area in area_type.areas.all()
        ]
        context['areas'] = areas
        context['area_type'] = area_type
        return context


class PoliticiansTemplateView(TemplateView):

    def generateAreaLink(self, area):
        typeName = AreaExtra.objects.select_related('base', 'type').get(base__id=area.id)._type_cache.name
        return reverse(
            'politicians-view',
            kwargs={
                'type_and_area_ids': '{type}-{area_id}'.format(
                    type=typeName,
                    area_id=area.id
                ),
                'ignored_slug': slugify(area.name)
            }
        )

    def __getAreaParent(self, area):
        try:
           return pmodels.Area.objects.get(id=area.parent_id)
        except pmodels.Area.DoesNotExist:
           return None

    def __createBreadCrumb(self):
        areaId = self.type_and_area[1]
        self.parentArea = pmodels.Area.objects.get(id=areaId)

        self.breadCrumb = []
        
        parentOfParent = self.__getAreaParent(self.parentArea)
        while parentOfParent:
            self.breadCrumb.insert(0,(parentOfParent.name, self.generateAreaLink(parentOfParent)))
            parentOfParent = self.__getAreaParent(parentOfParent)


    def get(self, request, *args, **kwargs):
        type_and_area = kwargs['type_and_area_ids']
        m = re.search(r'^([A-Z0-9]+?)-([-a-zA-Z0-9\:_]+)$', type_and_area)
        if not m:
            message = _("Malformed type and area: '{0}'")
            return HttpResponseBadRequest(message.format(type_and_area))
        self.type_and_area = m.groups()
        self.__createBreadCrumb()
        response = super(PoliticiansTemplateView, self).get(request, *args, **kwargs)
        return response


class PoliticiansView(PoliticiansTemplateView):
    template_name = 'candidates/politicians.html'
    memberships = {}

    def __rename_attribute(self, object_, old_attribute_name, new_attribute_name):
        setattr(object_, new_attribute_name, getattr(object_, old_attribute_name))
        delattr(object_, old_attribute_name)

    def __renameMembershipsProperties(self, memberships):
        for membership in memberships:
            self.__rename_attribute(membership, '_organization_cache', 'organization')
            self.__rename_attribute(membership, '_post_cache', 'post')
            self.__rename_attribute(membership, '_person_cache', 'person')
            self.__generatePersonUrl(membership.person)

    def __generatePersonUrl(self, person):
        person.url = reverse('person-view', kwargs={'person_id': person.id, 'ignored_slug': person.name})

    def __getAreaMemberships(self, areaId):
        powers = pmodels.Organization.objects.only('id','name').filter(parent_id=None, classification="poder")
        organisms = {}
        for power in powers:
            organisms[power.name] = self.__createOrganismsList(power.id, areaId)
        return organisms

    def __createMembershipsDict(self, parentId, areaId):
        membershipsDict = {}
        memberships = pmodels.Membership.objects.select_related('organization','post','person').filter(organization__classification='goverment', area_id=areaId, organization__parent_id=parentId)
        self.__renameMembershipsProperties(memberships)

        for membership in memberships:
            organizationId = membership.organization.id
            self.memberships[organizationId] = membership
            membershipsDict[organizationId] = self.__createMembershipsDict(organizationId, areaId)

        return membershipsDict

    def __createOrganismsListR(self, membershipsDict, organismsList, indent):
        for organizationId, children in membershipsDict.items():
            membership = self.memberships[organizationId]
            organismsList.append((indent, membership))
            if children:
                self.__createOrganismsListR(children, organismsList, indent + 1)

    def __createOrganismsList(self, powerId, areaId):
        organismsDict = self.__createMembershipsDict(powerId, areaId)
        organismsList = []
        self.__createOrganismsListR(organismsDict, organismsList, 0)

        return organismsList

    def get_context_data(self, **kwargs):
        context = super(PoliticiansView, self).get_context_data(**kwargs)
        areaId = self.type_and_area[1]
        parentArea = pmodels.Area.objects.get(id=areaId)

        context['internal_areas_count'] = pmodels.Area.objects.filter(parent_id=areaId).count()
        context['area_name'] = parentArea.name
        context['area_id'] = areaId
        context['redirect_after_login'] = reverse('create-politician-view', kwargs={'area_id': areaId})
        context['politician_list_edits_allowed'] = get_edits_allowed(self.request.user, False)
        context['internal_areas_url'] = '/politicians-areas/' + kwargs['type_and_area_ids'] + '/' + slugify(parentArea.name)
        context['bread_crumb'] = self.breadCrumb
        context['memberships'] = self.__getAreaMemberships(areaId)

        return context

class PoliticiansAreasView(PoliticiansTemplateView):
    template_name = 'candidates/politicians_areas.html'

    def get_context_data(self, **kwargs):
        context = super(PoliticiansAreasView, self).get_context_data(**kwargs)
        internalAreas = pmodels.Area.objects.filter(parent_id=self.parentArea.id)

        context['internal_areas_urls'] = []
        for internalArea in internalAreas:
            context['internal_areas_urls'].append((internalArea.name, self.generateAreaLink(internalArea) ))

        context['internal_areas_urls'] = sorted(context['internal_areas_urls'], key=lambda x: x[0])
        context['area_name'] = self.parentArea.name
        context['bread_crumb'] = self.breadCrumb

        return context
