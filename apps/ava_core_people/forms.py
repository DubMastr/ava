from django.forms import ModelForm, Form
from django.forms.models import inlineformset_factory
from apps.ava_core_people.models import Person,  Identifier


class PersonForm(ModelForm):
    class Meta:
        model = Person
        fields = ('firstname',  'surname')
        labels = {
            'firstname': ('Firstname'),
            'surname': ('Surname/Family Name'),
        }
        help_texts = {
                'firstname': (''),
                'surname': (''),
        }

IdentifierFormSet = inlineformset_factory(Person,  Identifier)
