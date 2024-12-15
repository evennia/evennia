# Large Language Model ("Chat-bot AI") integration

Contribution by Griatch 2023

This adds an LLMClient that allows Evennia to send prompts to a  LLM server (Large Language Model, along the lines of ChatGPT). Example uses a local OSS LLM install. Included is an NPC you can chat with using a new `talk` command. The NPC will respond using the AI responses from the LLM server. All calls are asynchronous, so if the LLM is slow, Evennia is not affected.

    > create/drop villager:evennia.contrib.rpg.llm.LLMNPC
    You create a new LLMNPC: villager

    > talk villager Hello there friend, what's up?
    You say (to villager): Hello there friend, what's up?
    villager says (to You): Hello! Not much going on, really.

    > talk villager Do you know where we are?
    You say (to villager): Do you know where we are?
    villager says (to You): We are in this strange place called 'Limbo'. Not much to do here.

## Installation

You need two components for this contrib - Evennia, and an LLM webserver that operates and provides an API to an LLM AI model.

### LLM Server

There are many LLM servers, but they can be pretty technical to install and set up. This contrib was tested with [text-generation-webui](https://github.com/oobabooga/text-generation-webui). It has a lot of features while also being easy to install. |

1. [Go to the Installation section](https://github.com/oobabooga/text-generation-webui#installation) and grab the 'one-click installer' for your OS.
2. Unzip the files in a folder somewhere on your hard drive (you don't have to put it next to your evennia stuff if you don't want to).
3. In a terminal/console, `cd` into the folder and execute the source file in whatever way it's done for your OS (like `source start_linux.sh` for Linux, or `.\start_windows` for Windows). This is an installer that will fetch and install everything in a conda virtual environment. When asked, make sure to select your GPU (NVIDIA/AMD etc) if you have one, otherwise use CPU.
4. Once all is loaded, stop the server with `Ctrl-C` (or `Cmd-C`) and open the file `webui.py` (it's one of the top files in the archive you unzipped). Find the text string `CMD_FLAGS = ''` near the top and change this to `CMD_FLAGS = '--api'`. Then save and close. This makes the server activate its api automatically.
4. Now just run that server starting script (`start_linux.sh` etc) again. This is what you'll use to start the LLM server henceforth.
5. Once the server is running, point your browser to http://127.0.0.1:7860 to see the running Text generation web ui running. If you turned on the API, you'll find it's now active on port 5000. This should not collide with default Evennia ports unless you changed something.
6. At this point you have the server and API, but it's not actually running any Large-Language-Model (LLM) yet. In the web ui, go to the `models` tab and enter a github-style path in the `Download custom model or LoRA` field.  To test so things work, enter `DeepPavlov/bart-base-en-persona-chat` and download. This is a small model (350 million parameters) so should be possible to run on most machines using only CPU. Update the models in the drop-down on the left and select it, then load it with the `Transformers` loader. It should load pretty quickly. If you want to load this every time, you can select the `Autoload the model` checkbox; otherwise you'll need to select and load the model every time you start the LLM server.
7. To experiment, you can find thousands of other open-source text-generation LLM models on [huggingface.co/models](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending). Beware to not download a too huge model; your machine may not be able to load it! If you try large models, _don't_ set the `Autoload the model` checkbox, in case the model crashes your server on startup.

For troubleshooting, you can look at the terminal output of the `text-generation-webui` server; it will show you the requests you do to it and also list any errors. See the text-generation-webui homepage for more details.

### Evennia config

To be able to talk to NPCs, import and add the `evennia.contrib.rpg.llm.llm_npc.CmdLLMTalk` to your default cmdset in `mygame/commands/default_cmdsets.py`:

```py
# in mygame/commands/default_cmdsets.py

# ... 
from evennia.contrib.rpg.llm import CmdLLMTalk  # <----

class CharacterCmdSet(default_cmds.CharacterCmdSet): 
    # ...
    def at_cmdset_creation(self): 
        # ... 
        self.add(CmdLLMTalk())     # <-----


```

See this [the tutorial on adding commands](Beginner-Tutorial-Adding-Commands) for more info. 

The default LLM api config should work with the `text-generation-webui` LLM server running its API on port 5000. You can also customize it via settings (if a setting is not added, the default below is used):

```python
# in mygame/server/conf/settings.py

# path to the LLM server
LLM_HOST = "http://127.0.0.1:5000"
LLM_PATH = "/api/v1/generate"

# if you wanted to authenticated to some external service, you could
# add an Authenticate header here with a token
# note that the content of each header must be an iterable
LLM_HEADERS = {"Content-Type": ["application/json"]}

# this key will be inserted in the request, with your user-input
LLM_PROMPT_KEYNAME = "prompt"

# defaults are set up for text-generation-webui and most models
LLM_REQUEST_BODY = {
    "max_new_tokens": 250,  # set how many tokens are part of a response
    "temperature": 0.7, # 0-2. higher=more random, lower=predictable
}
# helps guide the NPC AI. See the LLNPC section.
LLM_PROMPT_PREFIX = (
  "You are roleplaying as {name}, a {desc} existing in {location}. "
  "Answer with short sentences. Only respond as {name} would. "
  "From here on, the conversation between {name} and {character} begins."
)
```
Don't forget to reload Evennia (`reload` in game, or `evennia reload` from the terminal) if you make any changes. 

It's also important to note that the `PROMPT_PREFIX` needed by each model depends on how they were trained. There are a bunch of different formats. So you need to look into what should be used for each model you try. Report your findings!

## Usage

With the LLM server running and the new `talk` command added, create a new LLM-connected NPC and talk to it in-game.

    > create/drop girl:evennia.contrib.rpg.llm.LLMNPC
    > talk girl Hello!
    You say (to girl): Hello
    girl ponders ...
    girl says (to You): Hello! How are you?

The  conversation will be echoed to everyone in the room. The NPC will show a thinking/pondering message if the server responds slower than 2 seconds (by default).

## Primer on open-source LLM models 

[Hugging Face](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending) is becoming a sort of standard for downloading OSS models. In the `text generation` category (which is what we want for chat bots), there are some 20k models to choose from (2023). Just to get you started, check out models by [TheBloke](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending&search=TheBloke). TheBloke has taken on 'quantizing' (lowering their resolution) models released by others for them to fit on consumer hardware. Models from TheBloke follows roughly this naming standard: 

	TheBloke/ModelName-ParameterSize-other-GGML/GPTQ

For example

	TheBloke/Llama-2-7B-Chat-GGML
	TheBloke/StableBeluga-13B-GPTQ

Here, `Llama-2` is a 'base model' released open-source by Meta for free (also commercial) use. A base model takes millions of dollars and a supercomputer to train from scratch. Then others "fine tune" that base model. The `StableBeluga` model is created by someone partly retraining the `Llama-2` to make it more focused in some particular area, like chatting in a particular style. 
 
Models come in sizes, given as number of parameters they have, sort of how many 'neurons' they have in their brain. In the two examples above, the top one has `7B` - 7 billion parameters and the second `13B` - 13 billion. The small model we suggested to try during install is only `0.35B` by comparson.

Running these models in their base form would still not be possible to do without people like TheBloke "quantizing" them, basically reducing their precision. Quantiziation are given in byte precision. So if the original supercomputer version uses 32bit precision, the model you can actually run on your machine often only uses 8bit or 4bit resolution. The common wisdom seems to be that being able to run a model with more parameters at low resolution is better than a smaller one with a higher resolution.

You will see GPTQ or GGML endings to TheBloke's quantized models. Simplified, GPTQ are the main quantized models. To run this model, you need to have a beefy enough GPU to be able to fit the entire model in VRAM. GGML, in contrast, allows you to offload some of the model to normal RAM and use your CPU intead. Since you probably have more RAM than VRAM, this means you can run much bigger models this way, but they will run much slower. 

Moreover, you need additional memory space for the _context_ of the model. If you are chatting, this would be the chat history. While this sounds like it would just be some text, the length of the context determines how much the AI must 'keep in mind' in order to draw conclusions. This is measured in 'tokens' (roughly parts of words). Common context length is 2048 tokens, and a model must be specifically trained to be able to handle longer contexts. 

Here are some rough estimates of hardware requirements for the most common model sizes and 2048 token context. Use GPTQ models if you have enough VRAM on your GPU, otherwise use GMML models to also be able to put some or all data in RAM. 

| Model size | approx VRAM or RAM needed (4bit / 8bit) |
| --- | --- |
| 3B  | 1.5 GB / 3 GB
| 7B  | 3.5 GB / 7 GB | 
| 13B | 7 GB/13 GB | 
| 33B | 14 GB / 33 GB |
| 70B | 35 GB / 70 GB |

The results from a 7B or  even a 3B  model can be astounding! But set your expectations. Current (2023) top of the line consumer gaming GPUs have 24GB or VRAM and can at most fit a 33B 4bit quantized model at full speed (GPTQ). 

By comparison, Chat-GPT 3.5 is a 175B model. We don't know how large Chat-GPT 4 is, but it may be up to 1700B. For this reason you may also consider paying a commercial provider to run the model for you, over an API. This is discussed a little later, but try running locally with a small model first to see everything worls.


## Using an AI cloud service

You could also call out to an external API, like OpenAI (chat-GPT) or Google. Most cloud-hosted services are commercial and costs money. But since they have the hardware to run bigger models (or their own, proprietary models), they may give better and faster results.

```{warning}
Calling an external API is currently untested, so report any findings. Since the Evennia Server (not the Portal) is doing the calling, you are recommended to put a proxy between you and the internet if you call out like this.

```
Here is an untested example of the Evennia setting for calling [OpenAI's v1/completions API](https://platform.openai.com/docs/api-reference/completions):

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

> TODO: OpenAI's more modern [v1/chat/completions](https://platform.openai.com/docs/api-reference/chat) api does currently not work out of the gate since it's a bit more complex.

## The LLMNPC class

The LLM-able NPC class has a new method `at_talked_to` which does the connection to the LLM server and responds. This is called by the new `talk` command. Note that all these calls are asynchronous, meaning a slow response will not block Evennia.

The NPC's AI is controlled with a few extra properties and Attributes, most of which can be customized directly in-game by a builder.

### `prompt_prefix`

The `prompt_prefix` is very important. This will be added in front of your prompt and helps the AI know how to respond. Remember that an LLM model is basically an auto-complete mechaniss, so by providing examples and instructions in the prefix, you can help it respond in a better way.

The prefix string to use for a given NPC is looked up from one of these locations, in order:

1. An Attribute `npc.db.chat_prefix` stored on the NPC (not set by default)
2. A property `chat_prefix` on the the LLMNPC class (set to `None` by default).
3. The `LLM_PROMPT_PREFIX` setting (unset by default)
4. If none of the above locations are set, the following default is used:

       "You are roleplaying as {name}, a {desc} existing in {location}.
       Answer with short sentences. Only respond as {name} would.
       From here on, the conversation between {name} and {character} begins."

Here, the formatting tag `{name}` is replaced with the NPCs's name, `desc` by it's description, the `location` by its current location's name and `character` by the one talking to it. All names of characters are given by the `get_display_name(looker)` call, so this may be different
from person to person.

Depending on the model, it can be very important to extend the prefix both with more information about the character as well as communication examples. A lot of tweaking may be necessary before producing something remniscent of human speech.

### Response template

The `response_template` AttributeProperty defaults to being

    $You() $conj(say) (to $You(character)): {response}"

following common `msg_contents` [FuncParser](FuncParser) syntax. The `character` string will be mapped to the one talking to the NPC and the `response` will be what is said by the NPC.

### Memory

The NPC remembers what has been said to it by each player. This memory will be included with the prompt to the LLM and helps it understand the context of the conversation. The length of this memory is given by the `max_chat_memory_size` AttributeProperty. Default is 25 messages.  Once the memory is maximum is reached, older messages are forgotten. Memory is stored separately for each player talking to the NPC.

### Thinking

If the LLM server is slow to respond, the NPC will echo a random 'thinking message' to show it has not forgotten about you (something like "The villager ponders your words ...").

They are controlled by two `AttributeProperties` on the LLMNPC class:

- `thinking_timeout`: How long, in seconds to wait before showing the message. Default is 2 seconds.
- `thinking_messages`: A list of messages to randomly pick between. Each message string can contain `{name}`, which will be replaced by the NPCs name.


## TODO

There is a lot of expansion potential with this contrib. Some ideas:

- Easier support for different cloud LLM provider API structures.
- More examples of useful prompts and suitable models for MUD use.
