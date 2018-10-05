from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm, UsernameField
from evennia.utils import class_from_module
from random import choice, randint

class AccountForm(UserCreationForm):
    
    class Meta:
        model = class_from_module(settings.BASE_ACCOUNT_TYPECLASS)
        fields = ("username", "email")
        field_classes = {'username': UsernameField}
    
    email = forms.EmailField(help_text="A valid email address. Optional; used for password resets.", required=False)
    
class CharacterForm(forms.Form):
    name = forms.CharField(help_text="The name of your intended character.")
    age = forms.IntegerField(min_value=3, max_value=99, help_text="How old your character should be once spawned.")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), max_length=2048, min_length=160, required=False)
    
    @classmethod
    def assign_attributes(cls, attribute_list, points, min_points, max_points):
        """
        Randomly distributes a number of points across the given attributes,
        while also ensuring each attribute gets at least a certain amount
        and at most a certain amount.
        
        Args:
            attribute_list (iterable): List or tuple of attribute names to assign
                points to.
            points (int): Starting number of points
            min_points (int): Least amount of points each attribute should have
            max_points (int): Most amount of points each attribute should have
            
        Returns:
            spread (dict): Dict of attributes and a point assignment.
            
        """
        num_buckets = len(attribute_list)
        point_spread = (x for x in self.random_distribution(points, num_buckets, min_points, max_points))
        
        # For each field, get the point calculation for the next attribute value generated
        return {attribute: next(point_spread) for k in attribute_list}
    
    @classmethod
    def random_distribution(cls, points, num_buckets, min_points, max_points):
        """
        Distributes a set number of points randomly across a number of 'buckets'
        while also attempting to ensure each bucket's value finishes within a 
        certain range.
        
        If your math doesn't add up (you try to distribute 5 points across 100
        buckets and insist each bucket has at least 20 points), the algorithm
        will return the best spread it could achieve but will not raise an error
        (so in this case, 5 random buckets would get 1 point each and that's all).
        
        Args:
            points (int): The number of points to distribute.
            num_buckets (int): The number of 'buckets' (or stats, skills, etc)
                you wish to distribute points to.
            min_points (int): The least amount of points each bucket should have.
            max_points (int): The most points each bucket should have.
            
        Returns:
            buckets (list): List of random point assignments.
        
        """
        buckets = [0 for x in range(num_buckets)]
        indices = [i for (i, value) in enumerate(buckets)]
    
        # Do this while we have eligible buckets, points to assign and we haven't
        # maxed out all the buckets.
        while indices and points and sum(buckets) <= (max_points * num_buckets):
            # Pick a random bucket index
            index = choice(indices)
           
            # Add to bucket
            buckets[index] = buckets[index] + 1
            points = points - 1
            
            # Get the indices of eligible buckets
            indices = [i for (i, value) in enumerate(buckets) if (value < min_points) or (value < max_points)]
            
        return buckets
    
class ExtendedCharacterForm(CharacterForm):
    
    GENDERS = (
        ('male', 'Male'),
        ('female', 'Female'),
        ('androgynous', 'Androgynous'),
        ('special', 'Special')
    )
    
    RACES = (
        ('human', 'Human'),
        ('elf', 'Elf'),
        ('orc', 'Orc'),
    )
    
    CLASSES = (
        ('civilian', 'Civilian'),
        ('warrior', 'Warrior'),
        ('thief', 'Thief'),
        ('cleric', 'Cleric')
    )
    
    PERKS = (
        ('strong', 'Extra strength'),
        ('nimble', 'Quick on their toes'),
        ('diplomatic', 'Fast talker')
    )
    
    name = forms.CharField(help_text="The name of your intended character.")
    age = forms.IntegerField(min_value=3, max_value=99, help_text="How old your character should be once spawned.")
    gender = forms.ChoiceField(choices=GENDERS, help_text="Which end of the multidimensional spectrum does your character most closely align with, in terms of gender?")
    race = forms.ChoiceField(choices=RACES, help_text="What race does your character belong to?")
    job = forms.ChoiceField(choices=CLASSES, help_text="What profession or role does your character fulfill or is otherwise destined to?")
    
    perks = forms.MultipleChoiceField(choices=PERKS, help_text="What extraordinary abilities does your character possess?")
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), max_length=2048, min_length=160, required=False)
    
    strength = forms.IntegerField(min_value=1, max_value=10)
    perception = forms.IntegerField(min_value=1, max_value=10)
    intelligence = forms.IntegerField(min_value=1, max_value=10)
    dexterity = forms.IntegerField(min_value=1, max_value=10)
    charisma = forms.IntegerField(min_value=1, max_value=10)
    vitality = forms.IntegerField(min_value=1, max_value=10)
    magic = forms.IntegerField(min_value=1, max_value=10)
    
    def __init__(self, *args, **kwargs):
        # Do all the normal initizliation stuff that would otherwise be happening
        super(ExtendedCharacterCreationForm, self).__init__(*args, **kwargs)
        
        # Given a pool of points, let's randomly distribute them across attributes.
        # First get a list of attributes
        attributes = ('strength', 'perception', 'intelligence', 'dexterity', 'charisma', 'vitality', 'magic')
        # Distribute a random number of points across them
        attrs = self.assign_attributes(attributes, 50, 1, 10)
        # Initialize the form with the results of the point distribution
        for field in attrs.keys():
            self.initial[field] = attrs[field]