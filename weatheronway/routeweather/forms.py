from django import forms

class RouteForm(forms.Form):
    origin = forms.CharField(label="Origin", max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Start location'}))
    destination = forms.CharField(label="Destination", max_length=200, widget=forms.TextInput(attrs={'placeholder': 'Destination'}))
    departure_time = forms.TimeField(label="Departure Time", widget=forms.TimeInput(attrs={'type': 'time'}))
