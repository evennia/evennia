# AWSstorage system

Contrib by The Right Honourable Reverend (trhr), 2020

This plugin migrates the Web-based portion of Evennia, namely images,
javascript, and other items located inside staticfiles into Amazon AWS (S3)
cloud hosting. Great for those serving media with the game.

Files hosted on S3 are "in the cloud," and while your personal
server may be sufficient for serving multimedia to a minimal number of users,
the perfect use case for this plugin would be:

- Servers supporting heavy web-based traffic (webclient, etc) ...
- With a sizable number of users ...
- Where the users are globally distributed ...
- Where multimedia files are served to users as a part of gameplay

Bottom line - if you're sending an image to a player every time they traverse a
map, the bandwidth reduction of using this will be substantial. If not, probably
skip this contrib.

## On costs

Note that storing and serving files via S3 is not technically free outside of
Amazon's "free tier" offering, which you may or may not be eligible for;
setting up a vanilla evennia server with this contrib currently requires 1.5MB
of storage space on S3, making the current total cost of running this plugin
~$0.0005 per year. If you have substantial media assets and intend to serve
them to many users, caveat emptor on a total cost of ownership - check AWS's
pricing structure.

# Technical details

This is a drop-in replacement that operates deeper than all of Evennia's code,
so your existing code does not need to change at all to support it.

For example, when Evennia (or Django), tries to save a file permanently (say, an
image uploaded by a user), the save (or load) communication follows the path:

    Evennia -> Django
    Django -> Storage backend
    Storage backend -> file storage location (e.g. hard drive)

[django docs](https://docs.djangoproject.com/en/3.0/ref/settings/#std:setting-STATICFILES_STORAGE)

This plugin, when enabled, overrides the default storage backend,
which defaults to saving files at mygame/website/, instead,
sending the files to S3 via the storage backend defined herein.

There is no way (or need) to directly access or use the functions here with
other contributions or custom code. Simply work how you would normally, Django
will handle the rest.


# Installation

## Set up AWS account

If you don't have an AWS S3 account, you should create one at
https://aws.amazon.com/ - documentation for AWS S3 is available at:
https://docs.aws.amazon.com/AmazonS3/latest/gsg/GetStartedWithS3.html

Credentials required within the app are AWS IAM Access Key and Secret Keys,
which can be generated/found in the AWS Console.

The following example IAM Control Policy Permissions can be added to
the IAM service inside AWS. Documentation for this can be found here:
https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html

Note that this is only required if you want to tightly secure the roles
that this plugin has access to.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "evennia",
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObjectAcl",
                "s3:GetObject",
                "s3:ListBucket",
                "s3:DeleteObject",
                "s3:PutObjectAcl"
            ],
            "Resource": [
                "arn:aws:s3:::YOUR_BUCKET_NAME/*",
                "arn:aws:s3:::YOUR_BUCKET_NAME"
            ]
        }
    ],
    [
      {
         "Sid":"evennia",
         "Effect":"Allow",
         "Action":[
            "s3:CreateBucket",
         ],
         "Resource":[
            "arn:aws:s3:::*"
         ]
       }
    ]
}
```

Advanced Users: The second IAM statement, CreateBucket, is only needed
for initial installation. You can remove it later, or you can
create the bucket and set the ACL yourself before you continue.

## Dependencies


This package requires the dependency "boto3 >= 1.4.4", the official
AWS python package. To install, it's easiest to just install Evennia's
extra requirements;

- Activate your `virtualenv`
- `cd` to the root of the Evennia repository. There should be an `requirements_extra.txt`
file here.
- `pip install -r requirements_extra.txt`

## Configure Evennia

Customize the variables defined below in `secret_settings.py`. No further
configuration is needed. Note the three lines that you need to set to your
actual values.

```python
# START OF SECRET_SETTINGS.PY COPY/PASTE >>>

AWS_ACCESS_KEY_ID = 'THIS_IS_PROVIDED_BY_AMAZON'
AWS_SECRET_ACCESS_KEY = 'THIS_IS_PROVIDED_BY_AMAZON'
AWS_STORAGE_BUCKET_NAME = 'mygame-evennia' # CHANGE ME! I suggest yourgamename-evennia

# The settings below need to go in secret_settings,py as well, but will
# not need customization unless you want to do something particularly fancy.

AWS_S3_REGION_NAME = 'us-east-1' # N. Virginia
AWS_S3_OBJECT_PARAMETERS = { 'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
                            'CacheControl': 'max-age=94608000', }
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % settings.AWS_BUCKET_NAME
AWS_AUTO_CREATE_BUCKET = True
STATICFILES_STORAGE = 'evennia.contrib.base_systems.awsstorage.aws-s3-cdn.S3Boto3Storage'

# <<< END OF SECRET_SETTINGS.PY COPY/PASTE
```

You may also store these keys as environment variables of the same name.
For advanced configuration, refer to the docs for django-storages.

After copying the above, run `evennia reboot`.

## Check that it works

Confirm that web assets are being served from S3 by visiting your website, then
checking the source of any image (for instance, the logo).  It should read
`https://your-bucket-name.s3.amazonaws.com/path/to/file`. If so, the system
works and you shouldn't need to do anything else.

# Uninstallation

If you haven't made changes to your static files (uploaded images, etc),
you can simply remove the lines you added to `secret_settings.py`. If you
have made changes and want to uninstall at a later date, you can export
your files from your S3 bucket and put them in /static/ in the evennia
directory.


# License

Draws heavily from code provided by django-storages, for which these contributors
are authors:

Marty Alchin (S3)
David Larlet (S3)
Arne Brodowski (S3)
Sebastian Serrano (S3)
Andrew McClain (MogileFS)
Rafal Jonca (FTP)
Chris McCormick (S3 with Boto)
Ivanov E. (Database)
Ariel Núñez (packaging)
Wim Leers (SymlinkOrCopy + patches)
Michael Elsdörfer (Overwrite + PEP8 compatibility)
Christian Klein (CouchDB)
Rich Leland (Mosso Cloud Files)
Jason Christa (patches)
Adam Nelson (patches)
Erik CW (S3 encryption)
Axel Gembe (Hash path)
Waldemar Kornewald (MongoDB)
Russell Keith-Magee (Apache LibCloud patches)
Jannis Leidel (S3 and GS with Boto)
Andrei Coman (Azure)
Chris Streeter (S3 with Boto)
Josh Schneier (Fork maintainer, Bugfixes, Py3K)
Anthony Monthe (Dropbox)
EunPyo (Andrew) Hong (Azure)
Michael Barrientos (S3 with Boto3)
piglei (patches)
Matt Braymer-Hayes (S3 with Boto3)
Eirik Martiniussen Sylliaas (Google Cloud Storage native support)
Jody McIntyre (Google Cloud Storage native support)
Stanislav Kaledin (Bug fixes in SFTPStorage)
Filip Vavera (Google Cloud MIME types support)
Max Malysh (Dropbox large file support)
Scott White (Google Cloud updates)
Alex Watt (Google Cloud Storage patch)
Jumpei Yoshimura (S3 docs)
Jon Dufresne
Rodrigo Gadea (Dropbox fixes)
Martey Dodoo
Chris Rink
Shaung Cheng (S3 docs)
Andrew Perry (Bug fixes in SFTPStorage)

The repurposed code from django-storages is released under BSD 3-Clause,
same as Evennia, so for detailed licensing, refer to the Evennia license.

# Versioning

This is confirmed to work for Django 2 and Django 3.


----

<small>This document page is generated from `evennia/contrib/base_systems/awsstorage/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
