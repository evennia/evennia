# Pseudo-random generator and registry

Contribution by Vincent Le Goff (vlgeoff), 2017

This utility can be used to generate pseudo-random strings of information
with specific criteria.  You could, for instance, use it to generate
phone numbers, license plate numbers, validation codes, in-game security 
passwords and so on. The strings generated will be stored and won't be repeated.

## Usage Example

Here's a very simple example:

```python

from evennia.contrib.utils.random_string_generator import RandomStringGenerator

# Create a generator for phone numbers
phone_generator = RandomStringGenerator("phone number", r"555-[0-9]{3}-[0-9]{4}")

# Generate a phone number (555-XXX-XXXX with X as numbers)
number = phone_generator.get()

# `number` will contain something like: "555-981-2207"
# If you call `phone_generator.get`, it won't give the same anymore.phone_generator.all()
# Will return a list of all currently-used phone numbers
phone_generator.remove("555-981-2207")

# The number can be generated again
```

## Importing

1. Import the `RandomStringGenerator` class from the contrib.
2. Create an instance of this class taking two arguments:
   - The name of the gemerator (like "phone number", "license plate"...).
   - The regular expression representing the expected results.
3. Use the generator's `all`, `get` and `remove` methods as shown above.

To understand how to read and create regular expressions, you can refer to
[the documentation on the re module](https://docs.python.org/2/library/re.html).
Some examples of regular expressions you could use:

- `r"555-\d{3}-\d{4}"`: 555, a dash, 3 digits, another dash, 4 digits.
- `r"[0-9]{3}[A-Z][0-9]{3}"`: 3 digits, a capital letter, 3 digits.
- `r"[A-Za-z0-9]{8,15}"`: between 8 and 15 letters and digits.
- ...

Behind the scenes, a script is created to store the generated information
for a single generator.  The `RandomStringGenerator` object will also
read the regular expression you give to it to see what information is
required (letters, digits, a more restricted class, simple characters...)...
More complex regular expressions (with branches for instance) might not be
available.
