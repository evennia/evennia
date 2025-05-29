# AWS存储系统

由 The Right Honourable Reverend (trhr) 提供的贡献，2020年

此插件将 Evennia 的基于 Web 的部分迁移到 Amazon AWS（S3）云托管，主要涉及图像、JavaScript 和其他位于 staticfiles 中的项目。非常适合那些在游戏中提供媒体的服务器。

托管在 S3 上的文件位于“云端”，虽然你的个人服务器可能足够支持少量用户的多媒体服务，但此插件的完美用例为：

- 支持大量基于 Web 的流量的服务器（Web客户端等）…
- 用户数量庞大…
- 用户分布在全球…
- 在游戏中向用户提供多媒体文件

底线是：如果每次玩家穿越地图时都要发送图像，使用此插件将大幅减少带宽消耗。如果没有，可能可以跳过此贡献。

## 关于成本

请注意，通过 S3 存储和提供文件并不是在亚马逊的“免费套餐”外技术上免费的，你可能会合格也可能不合格；当前，设置一个简单的 Evennia 服务器需要在 S3 上占用 1.5MB 的存储空间，使得运行此插件的当前总成本约为每年 ~$0.0005。如果你拥有大量媒体资产并打算向许多用户提供它们，请注意总体拥有成本 - 检查 AWS 的定价结构。

## 技术细节

这是一个直接的替换插件，操作深于 Evennia 的所有代码，因此你的现有代码无需改变即可支持它。

例如，当 Evennia（或 Django）试图永久保存文件（例如，用户上传的图像）时，保存（或加载）通信遵循以下路径：

```
Evennia -> Django
Django -> 存储后端
存储后端 -> 文件存储位置（例如，硬盘）
```

[django docs](https://docs.djangoproject.com/en/4.1/ref/settings/#std:setting-STATICFILES_STORAGE)

启用此插件后，它将覆盖默认的存储后端，默认情况下保存文件到 `mygame/website/`，而是将文件通过此处定义的存储后端发送到 S3。

**注意**：没有办法（或需要）直接访问或使用此处的功能与其他贡献或自定义代码。只需按照正常方式工作，Django 会处理其余部分。

## 安装

### 设置 AWS 帐户

如果你没有 AWS S3 帐户，请在 https://aws.amazon.com/ 创建一个 - AWS S3 的文档可在这里获得：
https://docs.aws.amazon.com/AmazonS3/latest/gsg/GetStartedWithS3.html

应用程序所需的凭据是 AWS IAM 访问密钥和秘密密钥，可以在 AWS 控制台中生成/找到。

以下示例 IAM 控制策略权限可以添加到 AWS 中的 IAM 服务。有关此内容的文档可以在此处找到：
https://docs.aws.amazon.com/IAM/latest/UserGuide/introduction.html

请注意，只有在你想严格控制此插件访问的角色时，才需要此步骤。

```json
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
        },
        {
            "Sid": "evennia",
            "Effect": "Allow",
            "Action": [
                "s3:CreateBucket"
            ],
            "Resource": [
                "arn:aws:s3:::*"
            ]
        }
    ]
}
```

**高级用户：** 第二个 IAM 语句 `CreateBucket` 仅在初始安装时需要。你可以稍后将其删除，或者你可以自己创建存储桶并设置 ACL 后继续。

## 依赖关系

此包需要依赖项 "boto3 >= 1.4.4"，这是官方的 AWS Python 包。安装时，最好直接安装 Evennia 的额外要求：

```bash
pip install evennia[extra]
```

如果你通过 `git` 安装 Evennia，你也可以：

- `cd` 到 Evennia 存储库的根目录。
- `pip install --upgrade -e .[extra]`

## 配置 Evennia

在 `secret_settings.py` 中自定义以下变量的值。无需进一步配置。请注意需要设置为实际值的三行。

```python
# START OF SECRET_SETTINGS.PY COPY/PASTE >>>

AWS_ACCESS_KEY_ID = 'THIS_IS_PROVIDED_BY_AMAZON'
AWS_SECRET_ACCESS_KEY = 'THIS_IS_PROVIDED_BY_AMAZON'
AWS_STORAGE_BUCKET_NAME = 'mygame-evennia' # CHANGE ME! 我建议使用你的游戏名称-evennia

# 下面的设置也需要放在 secret_settings.py 中，但除非你想做特别花哨的事情，否则不需要定制。

AWS_S3_REGION_NAME = 'us-east-1' # 新泽西州
AWS_S3_OBJECT_PARAMETERS = { 'Expires': 'Thu, 31 Dec 2099 20:00:00 GMT',
                            'CacheControl': 'max-age=94608000', }
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_CUSTOM_DOMAIN = '%s.s3.amazonaws.com' % AWS_STORAGE_BUCKET_NAME
AWS_AUTO_CREATE_BUCKET = True
STATICFILES_STORAGE = 'evennia.contrib.base_systems.awsstorage.aws-s3-cdn.S3Boto3Storage'

# <<< END OF SECRET_SETTINGS.PY COPY/PASTE
```

你也可以将这些密钥存储为相同名称的环境变量。有关高级配置，请参考 django-storages 的文档。

在复制上述内容后，运行 `evennia reboot`。

## 检查功能

通过访问你的网站，检查任何图像（例如，徽标）的源代码，确认 Web 资产正在从 S3 提供。它应该显示为 `https://your-bucket-name.s3.amazonaws.com/path/to/file`。如果是这样，系统工作正常，你就不需要做其他任何事情。

## 卸载

如果你没有更改静态文件（上传的图像等），则可以简单地删除你添加到 `secret_settings.py` 的行。如果你做了更改并希望稍后卸载，可以从 S3 存储桶导出文件并将它们放入 Evennia 目录中的 `/static/` 下。

## 许可证

此代码严重依赖于 django-storages 提供的代码，贡献者包括：

- Marty Alchin (S3)
- David Larlet (S3)
- Arne Brodowski (S3)
- Sebastian Serrano (S3)
- Andrew McClain (MogileFS)
- Rafal Jonca (FTP)
- Chris McCormick (S3 with Boto)
- Ivanov E. (Database)
- Ariel Núñez (packaging)
- Wim Leers (SymlinkOrCopy + patches)
- Michael Elsdörfer (Overwrite + PEP8 compatibility)
- Christian Klein (CouchDB)
- Rich Leland (Mosso Cloud Files)
- Jason Christa (patches)
- Adam Nelson (patches)
- Erik CW (S3 encryption)
- Axel Gembe (Hash path)
- Waldemar Kornewald (MongoDB)
- Russell Keith-Magee (Apache LibCloud patches)
- Jannis Leidel (S3 and GS with Boto)
- Andrei Coman (Azure)
- Chris Streeter (S3 with Boto)
- Josh Schneier (Fork maintainer, Bugfixes, Py3K)
- Anthony Monthe (Dropbox)
- EunPyo (Andrew) Hong (Azure)
- Michael Barrientos (S3 with Boto3)
- piglei (patches)
- Matt Braymer-Hayes (S3 with Boto3)
- Eirik Martiniussen Sylliaas (Google Cloud Storage native support)
- Jody McIntyre (Google Cloud Storage native support)
- Stanislav Kaledin (Bug fixes in SFTPStorage)
- Filip Vavera (Google Cloud MIME types support)
- Max Malysh (Dropbox large file support)
- Scott White (Google Cloud updates)
- Alex Watt (Google Cloud Storage patch)
- Jumpei Yoshimura (S3 docs)
- Jon Dufresne
- Rodrigo Gadea (Dropbox fixes)
- Martey Dodoo
- Chris Rink
- Shaung Cheng (S3 docs)
- Andrew Perry (Bug fixes in SFTPStorage)

从 django-storages 重用的代码根据 BSD 3-Clause 许可证发布，许可证与 Evennia 相同，因此有关详细许可，请参考 Evennia 许可证。

## 版本

确认此插件支持 Django 2 和 Django 3。


----

<small>此文档页面并非由 `evennia/contrib/base_systems/awsstorage/README.md`自动生成。如想阅读最新文档，请参阅原始README.md文件。</small>
