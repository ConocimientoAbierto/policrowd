from .field_mappings import form_simple_fields, form_complex_fields_locations

def get_person_as_version_data(person):
    from candidates.election_specific import AREA_POST_DATA
    result = {}
    person_extra = person.extra
    result['id'] = person.id
    for field, null_value in form_simple_fields.items():
        result[field] = getattr(person, field) or null_value
    for field in form_complex_fields_locations:
        result[field] = getattr(person_extra, field)
    result['other_names'] = [
        {
            'name': on.name,
            'note': on.note,
            'start_date': on.start_date,
            'end_date': on.end_date,
        }
        for on in person.other_names.all()
    ]
    result['identfiers'] = [
        {
            'scheme': i.scheme,
            'identifier': i.identifier,
        }
        for i in person.identifiers.all()
    ]
    result['image'] = person.image
    standing_in = {}
    party_memberships = {}
    for membership in person.memberships.filter(post__isnull=False):
        post = membership.post
        membership_extra = membership.extra
        if not membership_extra:
            continue
        election = membership_extra.election
        standing_in[election.slug] = {
            'post_id': post.id,
            'name': AREA_POST_DATA.shorten_post_label(post.label)
        }
        if person_extra.get_elected(election.slug):
            standing_in[election.slug]['elected'] = True
        party = membership.on_behalf_of
        party_memberships[election.slug] = {
            'id': party.id,
            'name': party.name,
        }
    result['standing_in'] = standing_in
    result['party_memberships'] = party_memberships
    return result

def revert_person_from_version_data(version_data):
    raise NotImplementedError()
