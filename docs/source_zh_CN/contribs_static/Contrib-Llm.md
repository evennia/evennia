# 大型语言模型（“聊天机器人 AI”）集成

由 Griatch 贡献，2023

此贡献添加了一个 LLMClient，使 Evennia 能够将提示发送到 LLM 服务器（大型语言模型，如 ChatGPT）。示例使用本地 OSS LLM 安装。包括一个可以使用新 `talk` 命令聊天的 NPC。NPC 将使用 LLM 服务器的 AI 响应进行回复。所有调用都是异步的，因此即使 LLM 速度慢，Evennia 也不受影响。

```
> create/drop villager:evennia.contrib.rpg.llm.LLMNPC
You create a new LLMNPC: villager

> talk villager Hello there friend, what's up?
You say (to villager): Hello there friend, what's up?
villager says (to You): Hello! Not much going on, really.

> talk villager Do you know where we are?
You say (to villager): Do you know where we are?
villager says (to You): We are in this strange place called 'Limbo'. Not much to do here.
```

## 安装

您需要两个组件来使用此贡献：Evennia 和一个 LLM 网络服务器，该服务器操作并提供 LLM AI 模型的 API。

### LLM 服务器

有很多 LLM 服务器，但它们的安装和设置可能相当技术性。此贡献使用 [text-generation-webui](https://github.com/oobabooga/text-generation-webui) 进行了测试。它有很多功能，同时也易于安装。

1. [转到安装部分](https://github.com/oobabooga/text-generation-webui#installation) 并获取适用于您的操作系统的“一键安装程序”。
2. 将文件解压缩到硬盘上的某个文件夹中（如果不想，可以不必将其放在 Evennia 文件旁边）。
3. 在终端/控制台中，`cd` 进入该文件夹，并以适合您的操作系统的方式执行源文件（例如，Linux 使用 `source start_linux.sh`，Windows 使用 `.\start_windows`）。这是一个安装程序，将在 conda 虚拟环境中获取并安装所有内容。当被询问时，请确保选择您的 GPU（NVIDIA/AMD 等），如果没有，则使用 CPU。
4. 加载完毕后，使用 `Ctrl-C`（或 `Cmd-C`）停止服务器，并打开文件 `webui.py`（它是您解压缩的存档中的顶级文件之一）。在顶部附近找到文本字符串 `CMD_FLAGS = ''` 并将其更改为 `CMD_FLAGS = '--api'`。然后保存并关闭。这会使服务器自动激活其 API。
5. 现在只需再次运行该服务器启动脚本（`start_linux.sh` 等）。这就是您以后用于启动 LLM 服务器的方式。
6. 服务器运行后，将浏览器指向 http://127.0.0.1:7860 以查看运行中的文本生成 Web UI。如果您打开了 API，您会发现它现在在端口 5000 上激活。这不应与默认的 Evennia 端口冲突，除非您更改了某些设置。
7. 此时您有了服务器和 API，但实际上还没有运行任何大型语言模型（LLM）。在 Web UI 中，转到 `models` 选项卡，在 `Download custom model or LoRA` 字段中输入 GitHub 风格的路径。为了测试是否正常工作，输入 `DeepPavlov/bart-base-en-persona-chat` 并下载。这是一个小模型（3.5 亿参数），因此应该可以在大多数仅使用 CPU 的机器上运行。在左侧下拉菜单中更新模型并选择它，然后使用 `Transformers` 加载器加载它。它应该加载得很快。如果您想每次都加载此模型，可以选择 `Autoload the model` 复选框；否则，您需要在每次启动 LLM 服务器时选择并加载模型。
8. 要进行实验，您可以在 [huggingface.co/models](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending) 上找到成千上万的其他开源文本生成 LLM 模型。注意不要下载太大的模型；您的机器可能无法加载它！如果您尝试大型模型，请不要设置 `Autoload the model` 复选框，以防模型在启动时崩溃您的服务器。

有关故障排除，您可以查看 `text-generation-webui` 服务器的终端输出；它将显示您对其的请求并列出任何错误。有关更多详细信息，请参阅 text-generation-webui 主页。

### Evennia 配置

为了能够与 NPC 交谈，在 `mygame/commands/default_cmdsets.py` 中导入并添加 `evennia.contrib.rpg.llm.llm_npc.CmdLLMTalk` 到您的默认 cmdset：

```python
# 在 mygame/commands/default_cmdsets.py 中

# ... 
from evennia.contrib.rpg.llm import CmdLLMTalk  # <----

class CharacterCmdSet(default_cmds.CharacterCmdSet): 
    # ...
    def at_cmdset_creation(self): 
        # ... 
        self.add(CmdLLMTalk())     # <-----

```

有关更多信息，请参阅[添加命令的教程](Beginner-Tutorial-Adding-Commands)。

默认的 LLM API 配置应与在端口 5000 上运行其 API 的 `text-generation-webui` LLM 服务器一起使用。您还可以通过设置自定义它（如果未添加设置，则使用以下默认值）：

```python
# 在 mygame/server/conf/settings.py 中

# LLM 服务器的路径
LLM_HOST = "http://127.0.0.1:5000"
LLM_PATH = "/api/v1/generate"

# 如果您想对某些外部服务进行身份验证，可以在此处添加带有令牌的认证头
# 注意，每个头的内容必须是可迭代的
LLM_HEADERS = {"Content-Type": ["application/json"]}

# 此键将插入到请求中，包含您的用户输入
LLM_PROMPT_KEYNAME = "prompt"

# 默认设置适用于 text-generation-webui 和大多数模型
LLM_REQUEST_BODY = {
    "max_new_tokens": 250,  # 设置响应中的令牌数量
    "temperature": 0.7, # 0-2。越高=越随机，越低=可预测
}
# 帮助指导 NPC AI。请参阅 LLNPC 部分。
LLM_PROMPT_PREFIX = (
  "You are roleplaying as {name}, a {desc} existing in {location}. "
  "Answer with short sentences. Only respond as {name} would. "
  "From here on, the conversation between {name} and {character} begins."
)
```

如果您进行了任何更改，不要忘记重新加载 Evennia（在游戏中使用 `reload`，或在终端中使用 `evennia reload`）。

还需要注意的是，每个模型所需的 `PROMPT_PREFIX` 取决于它们的训练方式。存在许多不同的格式。因此，您需要研究每个尝试的模型应该使用什么。报告您的发现！

## 用法

在 LLM 服务器运行并添加新 `talk` 命令后，创建一个新的 LLM 连接的 NPC 并在游戏中与其交谈。

```
> create/drop girl:evennia.contrib.rpg.llm.LLMNPC
> talk girl Hello!
You say (to girl): Hello
girl ponders ...
girl says (to You): Hello! How are you?
```

对话将回显给房间中的所有人。如果服务器响应时间超过 2 秒（默认），NPC 将显示思考/沉思消息。

## 开源 LLM 模型入门

[Hugging Face](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending) 正逐渐成为下载开源模型的标准。在 `text generation` 类别中（这正是我们为聊天机器人所需的），有大约 2 万个模型可供选择（2023 年）。为了让您入门，请查看 [TheBloke](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending&search=TheBloke) 的模型。TheBloke 承担了“量化”（降低分辨率）其他人发布的模型的任务，以便它们适合消费者硬件。TheBloke 的模型大致遵循以下命名标准：

```
TheBloke/ModelName-ParameterSize-other-GGML/GPTQ
```

例如：

```
TheBloke/Llama-2-7B-Chat-GGML
TheBloke/StableBeluga-13B-GPTQ
```

这里，`Llama-2` 是由 Meta 免费（也包括商业）使用的开源“基础模型”。从头开始训练基础模型需要数百万美元和一台超级计算机。然后其他人“微调”该基础模型。`StableBeluga` 模型是由某人部分重新训练 `Llama-2` 以使其更专注于某个特定领域，例如以某种特定风格进行聊天。

模型有不同的大小，以其拥有的参数数量表示，类似于它们大脑中有多少“神经元”。在上面的两个示例中，顶部的模型有 `7B` - 70 亿个参数，第二个有 `13B` - 130 亿个。与之相比，我们建议在安装过程中尝试的小模型仅有 `0.35B`。

以其基础形式运行这些模型仍然是不可能的，除非有像 TheBloke 这样的人“量化”它们，基本上降低了它们的精度。量化以字节精度给出。因此，如果原始超级计算机版本使用 32 位精度，您实际上可以在机器上运行的模型通常仅使用 8 位或 4 位分辨率。常识似乎是能够以低分辨率运行更多参数的模型比以高分辨率运行较小的模型更好。

您会看到 TheBloke 的量化模型有 GPTQ 或 GGML 结尾。简而言之，GPTQ 是主要的量化模型。要运行此模型，您需要拥有足够强大的 GPU，以便能够将整个模型装入 VRAM。相比之下，GGML 允许您将模型的一部分卸载到普通 RAM 并改用 CPU。由于您可能拥有的 RAM 比 VRAM 多，这意味着您可以以这种方式运行更大的模型，但它们的运行速度会更慢。

此外，您还需要额外的内存空间来存储模型的上下文。如果您正在聊天，这将是聊天记录。虽然这听起来像只是一些文本，但上下文的长度决定了 AI 必须“记住”多少内容才能得出结论。这是以“令牌”为单位测量的（大致为单词的部分）。常见的上下文长度为 2048 个令牌，并且必须专门训练模型以能够处理更长的上下文。

以下是最常见的模型大小和 2048 个令牌上下文的硬件需求的粗略估计。 如果您的 GPU 上有足够的 VRAM，请使用 GPTQ 模型，否则请使用 GMML 模型，以便能够将部分或全部数据放入 RAM。

| 模型大小 | 需要的 VRAM 或 RAM（4bit / 8bit） |
| --- | --- |
| 3B  | 1.5 GB / 3 GB
| 7B  | 3.5 GB / 7 GB | 
| 13B | 7 GB/13 GB | 
| 33B | 14 GB / 33 GB |
| 70B | 35 GB / 70 GB |

7B 甚至 3B 模型的结果可能令人惊讶！但要设定您的期望。当前（2023 年）顶级消费者游戏 GPU 具有 24GB 的 VRAM，最多可以以全速（GPTQ）容纳 33B 4bit 量化模型。

相比之下，Chat-GPT 3.5 是一个 175B 模型。我们不知道 Chat-GPT 4 的大小，但它可能高达 1700B。因此，您也可以考虑支付商业提供商通过 API 为您运行模型。稍后会对此进行一些讨论，但请先尝试使用小模型本地运行以查看一切是否正常。

## 使用 AI 云服务

您还可以调用外部 API，例如 OpenAI（chat-GPT）或 Google。大多数云托管服务都是商业化的，并且需要付费。但由于他们拥有运行更大模型（或他们自己的专有模型）的硬件，他们可能会提供更好和更快的结果。

```{warning}
调用外部 API 目前未经测试，因此请报告任何发现。由于 Evennia 服务器（而不是门户）正在进行调用，因此建议您在与互联网之间放置代理以进行此类调用。
```

以下是调用 [OpenAI 的 v1/completions API](https://platform.openai.com/docs/api-reference/completions) 的 Evennia 设置的未经测试的示例：

```python
LLM_HOST = "https://api.openai.com"
LLM_PATH = "/v1/completions"
LLM_HEADERS = {"Content-Type": ["application/json"],
               "Authorization": ["Bearer YOUR_OPENAI_API_KEY"]}
LLM_PROMPT_KEYNAME = "prompt"
LLM_REQUEST_BODY = {
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "max_tokens": 128,
                   }

```

> TODO: OpenAI 的更现代的 [v1/chat/completions](https://platform.openai.com/docs/api-reference/chat) API 目前无法开箱即用，因为它更复杂。

## LLMNPC 类

可使用 LLM 的 NPC 类有一个新方法 `at_talked_to`，它连接到 LLM 服务器并响应。这是由新的 `talk` 命令调用的。请注意，所有这些调用都是异步的，这意味着慢速响应不会阻塞 Evennia。

NPC 的 AI 由一些额外的属性和属性控制，其中大多数可以由构建者直接在游戏中进行自定义。

### `prompt_prefix`

`prompt_prefix` 非常重要。它将被添加到您的提示之前，并帮助 AI 知道如何响应。请记住，LLM 模型基本上是一个自动补全机制，因此通过在前缀中提供示例和说明，可以帮助它更好地响应。

为给定 NPC 使用的前缀字符串从以下位置之一查找，按顺序：

1. 存储在 NPC 上的属性 `npc.db.chat_prefix`（默认未设置）
2. LLMNPC 类上的属性 `chat_prefix`（默认设置为 `None`）。
3. `LLM_PROMPT_PREFIX` 设置（默认未设置）
4. 如果以上位置均未设置，则使用以下默认值：

```
"You are roleplaying as {name}, a {desc} existing in {location}.
Answer with short sentences. Only respond as {name} would.
From here on, the conversation between {name} and {character} begins."
```

在这里，格式化标签 `{name}` 将被替换为 NPC 的名称，`desc` 为其描述，`location` 为其当前位置的名称，`character` 为与其交谈的人。所有角色的名称均通过 `get_display_name(looker)` 调用给出，因此这可能因人而异。

根据模型的不同，扩展前缀以提供有关角色的更多信息以及通信示例可能非常重要。在产生类似人类语言的内容之前，可能需要进行大量调整。

### 响应模板

`response_template` 属性属性默认为：

```
$You() $conj(say) (to $You(character)): {response}"
```

遵循常见的 `msg_contents` [FuncParser](FuncParser) 语法。`character` 字符串将映射到与 NPC 交谈的人，`response` 将是 NPC 所说的内容。

### 记忆

NPC 记住每个玩家对它所说的话。此记忆将包含在对 LLM 的提示中，并帮助其理解对话的上下文。此记忆的长度由 `max_chat_memory_size` 属性属性给出。默认值为 25 条消息。达到记忆最大值后，较早的消息将被遗忘。记忆为与 NPC 交谈的每个玩家分别存储。

### 思考

如果 LLM 服务器响应缓慢，NPC 将回显随机的“思考消息”，以表明它没有忘记您（例如“村民沉思您的话语...”）。

它们由 LLMNPC 类上的两个 `AttributeProperties` 控制：

- `thinking_timeout`: 等待多长时间（以秒为单位）显示消息。默认值为 2 秒。
- `thinking_messages`: 一组消息以供随机选择。每个消息字符串可以包含 `{name}`，它将被 NPC 的名称替换。

## TODO

此贡献有很大的扩展潜力。一些想法：

- 更轻松地支持不同的云 LLM 提供商 API 结构。
- 更多适用于 MUD 使用的有用提示和合适模型的示例。
