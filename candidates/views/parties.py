from collections import defaultdict

from django.http import Http404
from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.shortcuts import get_object_or_404

from popolo.models import Organization, Membership

from cached_counts.models import CachedCount
from candidates.models import PostExtra
from elections.mixins import ElectionMixin


class PartyListView(ElectionMixin, TemplateView):
    template_name = 'candidates/party-list.html'

    def get_context_data(self, **kwargs):
        context = super(PartyListView, self).get_context_data(**kwargs)
        party_ids_with_any_candidates = set(
            CachedCount.objects.filter(count_type='party', count__gt=0). \
                values_list('object_id', flat=True)
        )
        parties = []
        for party in Organization.objects.filter(classification='Party'):
            if party.id in party_ids_with_any_candidates:
                parties.append((party.name, party.id))
        parties.sort()
        context['parties'] = parties
        return context


def get_post_group_stats(posts):
    total = 0
    candidates = 0
    proportion = 0
    for post, members in posts.items():
        total += 1
        candidates += len(members)
    if total > 0:
        proportion = candidates / float(total)
    return {
        'proportion': proportion,
        'total': total,
        'candidates': candidates,
        'missing': total - candidates,
        'show_all': proportion > 0.3,
    }


class PartyDetailView(ElectionMixin, TemplateView):
    template_name = 'candidates/party.html'

    def get_context_data(self, **kwargs):
        context = super(PartyDetailView, self).get_context_data(**kwargs)
        party_id = kwargs['organization_id']
        party = get_object_or_404(Organization, extra__slug=party_id)

        # Make the party emblems conveniently available in the context too:
        context['emblems'] = \
            [image for image in party.extra.images.order_by('-is_primary')]
        all_post_groups = PostExtra.objects.values_list('group', flat=True).distinct()
        by_post_group = {
            pg: {
                'stats': None,
                'posts_with_memberships': defaultdict(list)
            }
            for pg in all_post_groups
        }
        for membership in Membership.objects.filter(
            on_behalf_of=party,
            extra__election=self.election_data,
            role=self.election_data.candidate_membership_role
        ).select_related().prefetch_related('post__extra', 'person__extra'):
            person = membership.person
            post = membership.post
            post_group = post.extra.group
            by_post_group[post_group]['posts_with_memberships'][post].append({
                'membership': membership,
                'person': person,
                'post': post,
            })
        # That'll only find the posts that someone from the party is
        # actually standing for, so add any other posts...
        for post_extra in self.election_data.posts.select_related('base').all():
            post = post_extra.base
            post_group = post_extra.group
            post_group_data = by_post_group[post_group]
            posts_with_memberships = post_group_data['posts_with_memberships']
            posts_with_memberships.setdefault(post, [])
        context['party'] = party
        context['party_name'] = party.name
        for post_group, data in by_post_group.items():
            posts_with_memberships = data['posts_with_memberships']
            by_post_group[post_group]['stats'] = get_post_group_stats(
                posts_with_memberships
            )
            data['posts_with_memberships'] = sorted(
                posts_with_memberships.items(),
                key=lambda t: t[0].label,
            )
        context['candidates_by_post_group'] = sorted(
            [
                (pg, data) for pg, data
                in by_post_group.items()
                if pg in all_post_groups
            ],
            key=lambda k: k[0]
        )
        return context
