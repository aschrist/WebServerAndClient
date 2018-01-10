import django_filters.rest_framework
#from django.core.urlresolvers import reverse_lazy
from django.urls import reverse_lazy
from django.http import Http404
from django.shortcuts import get_object_or_404

from django.core.exceptions import PermissionDenied
from django.views.generic import ListView, CreateView, UpdateView
from braces import views

from rest_framework import viewsets
from rest_framework import filters
from rest_framework import mixins
from rest_framework import generics

from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions
from rest_framework.decorators import detail_route

from .models import Ambulance, Call, Base, AmbulanceRoute

from .forms import AmbulanceCreateForm, AmbulanceUpdateForm

from .serializers import AmbulanceSerializer

# Django views
                
# Ambulance list page
class AmbulanceListView(ListView):
    model = Ambulance
    template_name = 'ambulances/ambulance_list.html'
    context_object_name = "ambulances"

# Ambulance list page
class AmbulanceView(CreateView):
    model = Ambulance
    context_object_name = "ambulance_form"
    form_class = AmbulanceCreateForm
    success_url = reverse_lazy('ambulance')

    def get_context_data(self, **kwargs):
        context = super(AmbulanceView, self).get_context_data(**kwargs)
        context['ambulances'] = Ambulance.objects.all().order_by('id')
        return context

# Ambulance update page
class AmbulanceUpdateView(UpdateView):
    model = Ambulance
    form_class = AmbulanceUpdateForm
    template_name = 'ambulances/ambulance_edit.html'
    success_url = reverse_lazy('ambulance')

    def get_object(self, queryset=None):
        obj = Ambulance.objects.get(id=self.kwargs['pk'])
        return obj

    def get_context_data(self, **kwargs):
        context = super(AmbulanceUpdateView, self).get_context_data(**kwargs)
        context['identifier'] = self.kwargs['pk']
        return context

# Call list page
class CallView(ListView):
    model = Call
    template_name = 'ambulances/dispatch_list.html'
    context_object_name = "ambulance_call"

# Admin page
class AdminView(ListView):
    model = Call
    template_name = 'ambulances/dispatch_list.html'
    context_object_name = "ambulance_call"
    
# # AmbulanceStatus list page
# class AmbulanceStatusCreateView(CreateView):
#     model = AmbulanceStatus
#     context_object_name = "ambulance_status_form"
#     form_class = AmbulanceStatusCreateForm
#     success_url = reverse_lazy('status')

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusCreateView, self).get_context_data(**kwargs)
#         context['statuses'] = AmbulanceStatus.objects.all().order_by('id')
#         return context


# # AmbulanceStatus update page
# class AmbulanceStatusUpdateView(UpdateView):
#     model = AmbulanceStatus
#     form_class = AmbulanceStatusUpdateForm
#     template_name = 'ambulances/ambulance_status_edit.html'
#     success_url = reverse_lazy('status')

#     def get_object(self, queryset=None):
#         obj = AmbulanceStatus.objects.get(id=self.kwargs['pk'])
#         return obj

#     def get_context_data(self, **kwargs):
#         context = super(AmbulanceStatusUpdateView, self).get_context_data(**kwargs)
#         context['id'] = self.kwargs['pk']
#         return context


# Ambulance map page
class AmbulanceMap(views.JSONResponseMixin, views.AjaxResponseMixin, ListView):
    template_name = 'ambulances/ambulance_map.html'

    def get_queryset(self):
        return Ambulance.objects.all()


        
# Custom viewset that only allows listing, retrieving, and updating
class ListRetrieveUpdateViewSet(mixins.ListModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.UpdateModelMixin,
                                viewsets.GenericViewSet):
    pass


class ListCreateViewSet(mixins.ListModelMixin,
                        mixins.RetrieveModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    pass


# Defines viewsets
# Viewsets combine different request types (GET, PUSH, etc.) in a single view class
# class AmbulanceViewSet(ListRetrieveUpdateViewSet):

#     # Specify model to expose
#     queryset = Ambulance.objects.all()

#     # Specify the serializer to package the data in JSON
#     serializer_class = AmbulanceSerializer

#     # Specify django REST's filtering system
#     filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)

#     # Specify fields that user can filter GET by
#     filter_fields = ('identifier', 'status')


# class AmbulanceStatusViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = AmbulanceStatus.objects.all()
#     serializer_class = AmbulanceStatusSerializer


# class CallViewSet(ListCreateViewSet):
#     queryset = Call.objects.all()
#     serializer_class = CallSerializer


# class EquipmentCountViewSet(mixins.UpdateModelMixin, viewsets.GenericViewSet):
#     queryset = EquipmentCount.objects.all()
#     serializer_class = EquipmentCountSerializer


# class HospitalViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Hospital.objects.all()
#     serializer_class = HospitalSerializer
#     filter_backends = (django_filters.rest_framework.DjangoFilterBackend,)
#     filter_fields = ('name', 'address')


# class BaseViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = Base.objects.all()
#     serializer_class = BaseSerializer


# class AmbulanceRouteViewSet(ListCreateViewSet):
#     queryset = AmbulanceRoute.objects.all()
#     serializer_class = AmbulanceRouteSerializer