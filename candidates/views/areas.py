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
            print vars(area)
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
        print context['areas']
        context['area_type'] = area_type
        return context


class PoliticiansTemplateView(TemplateView):
    def get(self, request, *args, **kwargs):
        type_and_area = kwargs['type_and_area_ids']
        m = re.search(r'^([A-Z0-9]+?)-([-a-zA-Z0-9\:_]+)$', type_and_area)
        if not m:
            message = _("Malformed type and area: '{0}'")
            return HttpResponseBadRequest(message.format(type_and_area))
        self.type_and_area = m.groups()
        response = super(PoliticiansTemplateView, self).get(request, *args, **kwargs)
        return response


class PoliticiansView(TemplateView):
    template_name = 'candidates/politicians.html'

    def get(self, request, *args, **kwargs):
        type_and_area = kwargs['type_and_area_ids']
        m = re.search(r'^([A-Z0-9]+?)-([-a-zA-Z0-9\:_]+)$', type_and_area)
        if not m:
            message = _("Malformed type and area: '{0}'")
            return HttpResponseBadRequest(message.format(type_and_area))
        self.type_and_area = m.groups()
        response = super(PoliticiansView, self).get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = super(PoliticiansView, self).get_context_data(**kwargs)
        #areaType = self.type_and_area[0]
        areaId = self.type_and_area[1]
        parentArea = pmodels.Area.objects.get(id=areaId)

        context['area_name'] = parentArea.name
        context['children_areas_url'] = '/politicians-areas/' + kwargs['type_and_area_ids'] + '/' + parentArea.name
        return context

class PoliticiansAreasView(TemplateView):
    template_name = 'candidates/politicians_areas.html'

    def get(self, request, *args, **kwargs):
        type_and_area = kwargs['type_and_area_ids']
        m = re.search(r'^([A-Z0-9]+?)-([-a-zA-Z0-9\:_]+)$', type_and_area)
        if not m:
            message = _("Malformed type and area: '{0}'")
            return HttpResponseBadRequest(message.format(type_and_area))
        self.type_and_area = m.groups()
        response = super(PoliticiansAreasView, self).get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = super(PoliticiansAreasView, self).get_context_data(**kwargs)

        areaId = self.type_and_area[1]
        parentArea = pmodels.Area.objects.get(id=areaId)

        areaChildren = AreaExtra.objects \
                    .select_related('base', 'type') \
                    .filter(base__parent_id=areaId)

        context['internal_areas_urls'] = []
        for areaChild in areaChildren:
            childArea = areaChild._base_cache
            childType = areaChild._type_cache
            context['internal_areas_urls'].append((childArea.name, '/politicians/' + childType.name + '-' + str(childArea.id) + "/" + childArea.name))

        context['internal_areas_urls'] = sorted(context['internal_areas_urls'], key=lambda x: x[0])

        context['area_name'] = parentArea.name

        return context
