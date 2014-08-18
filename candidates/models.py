from django.db import models

# Create your models here.

class PopItPerson(object):

    def __init__(self, api=None, popit_data=None):
        self.popit_data = popit_data
        self.api = api
        self.party = None

    @classmethod
    def create_from_popit(cls, api, popit_person_id):
        popit_data = api.persons(popit_person_id).get()['result']
        new_person = cls(api=api, popit_data=popit_data)
        new_person._update_party()
        return new_person

    @property
    def name(self):
        return self.popit_data['name']

    @property
    def id(self):
        return self.popit_data['id']

    def _update_party(self):
        for m in self.popit_data['memberships']:
            # FIXME: note that this fetches a huge object from the
            # API, since the organisation object for a party has a
            # list of all its memberships inline, which can be
            # hundreds of people for a major party. See the comment on
            # the related issue here:
            # https://github.com/mysociety/popit/issues/593#issuecomment-51690405
            o = self.api.organizations(m['organization_id']).get()['result']
            # FIXME: this is just quick and broken implementation -
            # it's obviously not correct, because if someone changes
            # parties between the 2010 and 2015 elections, they'll
            # have multiple party memberships, and this will pick one
            # at random.  However, at the moment there's no date
            # information for party memberships either, so let's deal
            # with that later.
            if o['classification'] == 'Party':
                self.party = o
                return