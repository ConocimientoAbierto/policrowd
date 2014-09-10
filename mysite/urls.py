from django.conf import settings
from django.conf.urls import patterns, include, url

from django.contrib import admin

from candidates.views import (ConstituencyPostcodeFinderView,
    ConstituencyNameFinderView, ConstituencyDetailView, CandidacyView,
    CandidacyDeleteView, NewPersonView, UpdatePersonView)

from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', ConstituencyPostcodeFinderView.as_view(), name='finder'),
    url(r'^lookup/name$', ConstituencyNameFinderView.as_view(), name='lookup-name'),
    url(r'^lookup/postcode$', ConstituencyPostcodeFinderView.as_view(), name='lookup-postcode'),
    url(r'^constituency/(?P<constituency_name>.*)$',
        ConstituencyDetailView.as_view(),
        name='constituency'),
    url(r'^candidacy$',
        CandidacyView.as_view(),
        name='candidacy-create'),
    url(r'^candidacy/delete$',
        CandidacyDeleteView.as_view(),
        name='candidacy-delete'),
    url(r'^person$',
        NewPersonView.as_view(),
        name='person-create'),
    url(r'^person/(?P<person_id>.*)/update$',
        UpdatePersonView.as_view(),
        name='person-update'),
    url(r'^admin/', include(admin.site.urls)),
)

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
