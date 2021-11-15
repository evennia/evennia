title: Such a small thing ...

--- 


Lately I went back to clean up and optimize the workings of Evennia's Attributes. I had a nice idea for making the code easier to read and also faster by caching more aggressively. The end result was of course that I managed to break things. In the end it took me two weeks to get my new scheme to a state where it did what it already did before (although faster).  
  
Doing so, some of the trickier aspects of implementing easily accessible Attributes came back into view, and I thought I'd cover them here. Python intricacies and black magic to follow. You have been warned.   
  
Attributes are, in Evennia lingo, arbitrary things a user may want to permanently store on an object, script or player. It could be numbers or strings like health, mana or short descriptions, but also more advanced stuff like lists, dictionaries or custom Python objects.  
  
Now, Evennia allows this syntax for defining an attribute on e.g. the object _myobj_:  

> myobj.db.test = [1,2,3,4]

This very Pythonic-looking thing allows a user to transparently save that list (or whatever) to an attribute named, in this example, _test._ This will save to the database.  
 What happens is that _db_, which is a special object defined on all Evennia objects, takes all attributes on itself and saves them by overloading its __setattr__ default method (you can actually skip writing _db_ most of the time, and just use this like you would any Python attribute, but that's another story).  
  
Vice-versa,  

> value = myobj.db.test

This makes use of the _db_ object's custom __get_attribute__ method behind the scenes. The _test_ attribute is transparently retrieved from the database (or cache) for you.  
  
Now, the (that is, my) headache comes when you try to do this:  

> myobj.db.test[3] = 5

Such a small, normal thing to do! Looks simple, right? It is actually trickier than it looks to allow for this basic functionality.  
The problem is that Python do everything by reference. The list is a separate object and has no idea it is connected to _db._ _db_'s __get_attribute__ is called, and happily hands over the list _test_. And then _db_ is out of the picture!. My nifty save-to-database feature (which sits in _db_) knows nothing about how the 3rd index of the list _test_ now has a 5 instead of a 4.  
  
Now, of course, you could always do this:  

> temp = myobj.db.test

> temp[3] = 5

> myobj.db.test = temp

This will work fine. It is however also clumsy and hardly intuitive. The only solution I have been able to come up with is to have _db_ return something which is _almost_ a list but not quite. It's in fact returning an object I not-so-imaginatively named a _PackedList__._ This object works just like a list, except all modifying methods on it makes sure to save the result to the database. So for example, what is called when you do mylist[3] = 4 is a method on the list named __setitem__. I overload this, lets it do its usual thing, then call the save.  

> myobj.db.test[3] = 5

now works fine, since _test_ is in fact a _PackedList_ and knows that changes to it should be saved to the database. I do the same for dictionaries and for nested combinations of lists and dictionaries. So all is nice and dandy, right?  Things work just like Python now?  
  
No, unfortunately not. Consider this:  

> myobj.db.test = [1, 3, 4, [5, 6, 7]]

A list with a list inside it. This is perfectly legal, and you can access all parts of this just fine:  

> val = myobj.db.test[3][2] # returns 7!

But how about _assigning_ data to that internal nested list?  

> myobj.db.test[3][2] = 8

We would now expect _test_ to be [1, 3, 4, [5, 6, 8]]. It is not. It is infact only [5, 6, 8]. The inner list has replaced the entire attribute!   
  
What actually happens here? _db_ returns a nested structure of two _PackedList_s. All nice and dandy.  But Python thinks they are two separate objects! The main list holds a reference to the internal list, but as far as I know _there is no way for the nested list to get the back-reference to the list holding it_! As far as the nested list knows, it is all alone in the world, and therefore there is no way to trigger a save in the "parent" list.  
 The result is that we update the nested list just fine - and that triggers the save operation to neatly overwrite the main list in the cache and the database.  
   
This latter problem is not something I've been able to solve. The only way around it seems to use a temporary variable, assign properly, then save it back, as suggested earlier. I'm thinking this is a fundamental limitation in the way cPython is implemented, but maybe I'm missing some clever hack here (so anyone reading who has a better solution)?  
  
Either way, the _db_ functionality makes for easy coding when saving things to the database, so despite it not working _quite_ like normal Python, I think it's pretty useful.