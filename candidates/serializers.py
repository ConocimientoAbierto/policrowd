import json

from django.core.urlresolvers import reverse

from rest_framework import serializers

from images.models import Image
from elections import models as election_models
from popolo import models as popolo_models


class OtherNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.OtherName
        fields = ('name', 'note')


class IdentifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Identifier
        fields = ('identifier', 'scheme')


class ContactDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.ContactDetail
        fields = ('contact_type', 'label', 'note', 'value')


class LinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Link
        fields = ('note', 'url')


class SourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = popolo_models.Source
        fields = ('note', 'url')


class AreaTypeSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = election_models.AreaType
        fields = ('name', 'source')


class AreaSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Area
        fields = (
            'id',
            'url',
            'name',
            'identifier',
            'classification',
            'other_identifiers',
            'parent',
            'type',
        )

    other_identifiers = IdentifierSerializer(many=True, read_only=True)
    type = AreaTypeSerializer(source='extra.type')


class ElectionSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = election_models.Election
        fields = (
            'id',
            'slug',
            'url',
            'name',
            'winner_membership_role',
            'candidate_membership_role',
            'election_date',
            'current',
            'use_for_candidate_suggestions',
            'area_types',
            'area_generation',
            'organization',
            'party_lists_in_use',
            'ocd_division',
            'description'
        )

    area_types = AreaTypeSerializer(many=True, read_only=True)


class FlatMembershipSerialzier(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Membership
        fields = (
            'label',
            'role',
            'person',
            'organization',
            'on_behalf_of',
            'post',
            'start_date',
            'end_date',
            'election',
        )

    election = ElectionSerializer(source='extra.election')


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = (
            'source',
            'is_primary',
            'md5sum',
            'copyright',
            'uploading_user',
            'user_notes',
            'user_copyright',
            'notes',
            'image_url',
        )

    md5sum = serializers.ReadOnlyField(source='extra.md5sum')
    copyright = serializers.ReadOnlyField(source='extra.copyright')
    uploading_user = serializers.ReadOnlyField(source='extra.uploading_user.username')
    user_notes = serializers.ReadOnlyField(source='extra.user_notes')
    user_copyright = serializers.ReadOnlyField(source='extra.user_copyright')
    notes = serializers.ReadOnlyField(source='extra.notes')
    image_url = serializers.SerializerMethodField()

    def get_image_url(self, i):
        return i.image.url

class OrganizationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Organization
        fields = (
            'id',
            'slug',
            'url',
            'name',
            'other_names',
            'identifiers',
            'classification',
            'parent',
            'founding_date',
            'dissolution_date',
            'contact_details',
            'images',
            'links',
            'sources',
        )

    slug = serializers.ReadOnlyField(source='extra.slug')
    contact_details = ContactDetailSerializer(many=True, read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    links = LinkSerializer(many=True, read_only=True)
    other_names = OtherNameSerializer(many=True, read_only=True)
    sources = SourceSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True, source='extra.images')


class JSONSerializerField(serializers.Field):
    def to_representation(self, value):
        return json.loads(value)


class PersonSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Person
        fields = (
            'id',
            'url',
            'name',
            'other_names',
            'identifiers',
            'honorific_prefix',
            'honorific_suffix',
            'sort_name',
            'email',
            'gender',
            'birth_date',
            'death_date',
            'versions',
            'contact_details',
            'links',
            'memberships',
            'images',
        )

    contact_details = ContactDetailSerializer(many=True, read_only=True)
    identifiers = IdentifierSerializer(many=True, read_only=True)
    links = LinkSerializer(many=True, read_only=True)
    other_names = OtherNameSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True, source='extra.images')

    versions = JSONSerializerField(source='extra.versions', read_only=True)

    memberships = FlatMembershipSerialzier(many=True, read_only=True)


class PostSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = popolo_models.Post
        fields = (
            'id',
            'url',
            'slug',
            'label',
            'role',
            'organization',
            'area',
            'elections',
            'memberships',
        )

    slug = serializers.ReadOnlyField(source='extra.slug')
    memberships = FlatMembershipSerialzier(many=True, read_only=True)

    elections = serializers.SerializerMethodField()

    def get_elections(self, post):
        return [
            self.context['request'].build_absolute_uri(
                reverse('election-detail', kwargs={
                    'pk': election.id,
                    'version': 'v0.9',
                })
            )
            for election in post.extra.elections.all()
        ]
