# Documentation Style Guide
This guide is intended to standardize the community documentation for Evennia. It outlines specifically what sort of 
information belongs in the documentation, where to place the information, and how information should be formatted.

## What is documentable?
Evennia's core documentation is split into the following key areas:
- Core/Evennia API
- Tutorials and Examples
- Community
- Related Topics
- Full API Reference

### Core/Evennia API
This section of the documentation is a game-agnostic tutorial for using specific structures available in the Evennia flat API.

The following types of information would be relevant here:
- Documentation of the features available in the Typeclass system
- Documentation about the Message Path and OOB communications
- Glossaries of Evennia terms, like what a "Puppet" is

The following types of information would be out of place:
- A tutorial on building a 'clothing' system. This is not game-agnostic; it would be more appropriate in the Tutorials section
- Documentation related to Apache/Nginx configuration. This is not an Evennia concept, this would belong in the Server section

### Tutorials and Examples
This section deals with specific systems that users can implement in their game. 

The following would be appropriate here:

- Documentation for a contrib
- A tutorial on how to build a 'clothing' system
- A tutorial on adding a Wikipedia page to your website

### Community
This section of the documentation surrounds the Evennia community. It includes subsections related to
the future of the Evennia project. Opinions also live here.

The following would be appropriate here:

- How Evennia's core repository uses Continual Integration
- How to get and give help in Evennia; official channels
- What we think Evennia is, and how we think it should be used
- A discussion of the potential for refactoring Evennia submodules

### Related Topics
This section of the documentation deals with the pieces of Evennia that are technically 'outside' of Evennia.

The following topics would be appropriate here:

- How to use Evennia to learn Python
- How to administer a production server running Evennia

### Full API Reference
This section is the technical documentation for Evennia. It is generated automatically
from the source of Evennia. It provides a detailed reference for specific modules.

## Formatting Documentation
The Evennia documentation uses Markdown formatting and the conventions defined in the Wikipedia
Manual of Style.

### Table of Contents
A table of contents should be present on each page of the documentation. This is generated
automatically when the documentation is built.

### Disambiguation
Disambiguation documents should be created to help redirect people who might search
the documentation. These pages are flagged with the following source code:

```python
TYPE = "Disambiguation"
```

Disambiguation pages should also be created when links are broken and pages renamed or move. 

### Rating

All pages receive a **rating** in the documentation. 

```python
RATING = "Exceptional"
```

The following ratings are available.

#### Unknown
Unknown quality articles have not yet been manually rated

#### Needs Improvement
Needs improvement pages have some or all of the following characteristics:
  - May be a stub article
  - Lacks information
  - Contains inaccurate information
  - Is not categorized

A stub article is a placeholder waiting for anyone to fill in. Creating stubs lets users know how
they can help improve documentation. Most stubs will be rated "Needs Improvement."

Not all pages that are 'short' need improvement. If they are concise and deal with a
specific topic, they may be quite short and still meet a higher quality rating.

#### Acceptable
  - Has a substantial number of broken links, very few links, or no links
  - Contains little or no accurate information

#### Excellent
  - No important information is missing
  - Has a sufficient number of working links
  - A sufficient number of other pages link to this page
  - Is properly categorized

#### Exceptional
Exceptional articles contain ALL of the following characteristics:

  - The topic is an important "must-read"
  - The topic is covered comprehensively
  - The information has been verified
  - No broken links are present
  - The article is aesthetically pleasing and free of grammar/spelling errors
  - The article is properly categorized
  
We do not expect every topic covered to reach "exceptional" status - in fact, the bar is set arbitrarily
high so that only a few topics ever will. This is intended to make the documentation more readable for
new users. Exceptional articles are well-maintained and updated with every release.

```python
class Documentation:
    RATING = "Acceptable"
```