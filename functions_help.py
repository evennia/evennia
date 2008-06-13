from apps.helpsys.models import HelpEntry
"""
Help system functions.
"""
def find_topicmatch(pobject, topicstr):
    """
    Searches for matching topics based on player's input.
    """
    is_staff = pobject.is_staff()
    if topicstr.isdigit():
        if is_staff:
            return HelpEntry.objects.filter(id=topicstr)
        else:
            return HelpEntry.objects.filter(id=topicstr).exclude(staff_only=1)
    else:
        if is_staff:
            return HelpEntry.objects.filter(topicname__istartswith=topicstr)
        else:
            return HelpEntry.objects.filter(topicname__istartswith=topicstr).exclude(staff_only=1)
    
def find_topicsuggestions(pobject, topicstr):
    """
    Do a fuzzier "contains" match.
    """
    is_staff = pobject.is_staff()
    if is_staff:
        return HelpEntry.objects.filter(topicname__icontains=topicstr)
    else:
        return HelpEntry.objects.filter(topicname__icontains=topicstr).exclude(staff_only=1)
