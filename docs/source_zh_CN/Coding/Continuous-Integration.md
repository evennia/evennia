# 持续集成 (CI)

[持续集成 (CI)](https://en.wikipedia.org/wiki/Continuous_integration) 是一种开发实践，要求开发人员将代码集成到共享的代码库中。每次提交都会通过自动构建进行验证，使团队能够及早发现问题。例如，可以设置为仅在测试通过后安全地将数据部署到生产服务器。

对于 Evennia，持续集成允许自动化构建过程来：

* 从源代码控制中拉取最新构建。
* 在支持的 SQL 数据库上运行迁移。
* 自动化该项目的其他独特任务。
* 运行单元测试。
* 将这些文件发布到服务器目录。
* 重载游戏。

## 持续集成指南

Evennia 本身大量使用 [GitHub Actions](https://github.com/features/actions)。这与 GitHub 集成，对于大多数人来说，尤其是如果您的代码已经在 GitHub 上，这是一个不错的选择。您可以在[这里](https://github.com/evennia/evennia/actions)查看和分析 Evennia 的 actions 运行情况。

然而，还有许多工具和服务提供 CI 功能。[这里有一个博客概述](https://www.atlassian.com/continuous-delivery/continuous-integration/tools)（外部链接）。
