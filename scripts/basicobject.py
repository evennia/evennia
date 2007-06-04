"""
This will be the base object type/interface that all scripts are derived from by
default. It will have the necessary outline for developers to sub-class and override.
"""

class BasicObject:
   def __init__(self, source_obj):
      """
      Get our ducks in a row.
      
      source_obj: (Object) A reference to the object being scripted (the child).
      """
      self.source_obj = source_obj
      
   def a_desc(self, looker):
      """
      Perform this action when someone uses the LOOK command on the object.
      
      looker: (Object) Reference to the looker
      """
      # Un-comment the line below for an example
      #print "SCRIPT TEST: %s looked at %s." % (looker, self.source_obj)
      pass
      
def class_factory(source_obj):
   """
   This method is called any script you retrieve (via the scripthandler). It
   creates an instance of the class and returns it transparently. I'm not
   sure how well this will scale, but we'll find out. We may need to
   re-factor this eventually.
   
   source_obj: (Object) A reference to the object being scripted (the child).
   """
   return BasicObject(source_obj)      