# Large Language Model ("Chat-bot AI") integration

Contribution by Griatch 2023

This adds an LLMClient that allows Evennia to send prompts to a  LLM server (Large Language Model, along the lines of ChatGPT). Example uses a local OSS LLM install. Included is an NPC you can chat with using a new `talk` command. The NPC will respond using the AI responses from the LLM server. All calls are asynchronous, so if the LLM is slow, Evennia is not affected.

```
> create/drop villager:evennia.contrib.rpg.llm.LLMNPC
You create a new LLMNPC: villager

> talk villager Hello there friend, what's up?
You say (to villager): Hello there friend, what's up?
villager says (to You): Hello! Not much going on, really. How about you?

> talk villager Just enjoying the nice weather.
You say (to villager): Just enjoying the nice weather.
villager says (to You): Yeah, it is really quite nice, ain't it.
```

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
6. At this point you have the server and API, but it's not actually running any Large-Language-Model (LLM) yet. In the web ui, go to the `models` tab and enter a github-style path in the `Download custom model or LoRA` field.  To test so things work, enter `facebook/opt-125m` and download. This is a relatively small model (125 million parameters) so should be possible to run on most machines using only CPU. Update the models in the drop-down on the left and select it, then load it with the `Transformers` loader. It should load pretty quickly. If you want to load this every time, you can select the `Autoload the model` checkbox; otherwise you'll need to select and load the model every time you start the LLM server.
7. To experiment, you can find thousands of other open-source text-generation LLM models on [huggingface.co/models](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending). Beware to not download a too huge model; your machine may not be able to load it! If you try large models, _don't_ set the `Autoload the model` checkbox, in case the model crashes your server on startup.

For troubleshooting, you can look at the terminal output of the `text-generation-webui` server; it will show you the requests you do to it and also list any errors. See the text-generation-webui homepage for more details.

### Evennia config

To be able to talk to NPCs, import and add the `evennia.contrib.rpg.llm.llm_npc.CmdLLMTalk` command to your Character cmdset in `mygame/commands/default_commands.py` (see the basic tutorials if you are unsure).

The default LLM api config should work with the text-generation-webui LLM server running its API on port 5000. You can also customize it via settings (if a setting is not added, the default below is used):

```python
    # path to the LLM server
    LLM_HOST = "http://127.0.0.1:5000"
    LLM_PATH = "/api/v1/generate"

    # if you wanted to authenticated to some external service, you could
    # add an Authenticate header here with a token
    LLM_HEADERS = {"Content-Type": "application/json"}

    # this key will be inserted in the request, with your user-input
    LLM_PROMPT_KEYNAME = "prompt"

    # defaults are set up for text-generation-webui and most models
    LLM_REQUEST_BODY = {
        "max_new_tokens": 250,  # set how many tokens are part of a response
        "temperature": 0.7, # 0-2. higher=more random, lower=predictable
    }
```
Don't forget to reload Evennia if you make any changes.


## Usage

With the LLM server running and the new `talk` command added, create a new LLM-connected NPC and talk to it in-game.

    > create/drop girl:evennia.contrib.rpg.llm.LLMNPC
    > talk girl Hello!
    You say (to girl): Hello
    girl ponders ...
    girl says (to You): Hello! How are you?

Most likely, your first response will *not* be this nice and short, but will be quite nonsensical, looking like an email. This is because the example model we loaded is not optimized for conversations. But at least you know it works!

The  conversation will be echoed to everyone in the room. The NPC will show a thinking/pondering message if the server responds slower than 2 seconds (by default). 

## A note on running LLMs locally

Running an LLM locally can be _very_ demanding.

As an example, I tested this on my very beefy work laptop. It has 32GB or RAM, but no gpu. so i ran the example (small 128m parameter) model on cpu. it takes about 3-4 seconds to generate a (frankly very bad) response. so keep that in mind.

On huggingface.co you can find listings of the 'best performing' language models right now. This changes all the time. The leading models require 100+ GB RAM. And while it's possible to run on a CPU, ideally you should have a large graphics card (GPU) with a lot of VRAM too.

So most likely you'll have to settle on something smaller. Experimenting with different models and also tweaking the prompt is needed.

Also be aware that many open-source models are intended for AI research and licensed for non-commercial use only. So be careful if you want to use this in a commercial game. No doubt there will be a lot of changes in this area over the coming years.

### Why not use an AI cloud service?

You could in principle use this to call out to an external API, like OpenAI (chat-GPT) or Google. Most cloud-hosted services are commercial and costs money. But since they have the hardware to run bigger models (or their own, proprietary models), they may give better and faster results.

Calling an external API is not tested, so report any findings. Since the Evennia Server (not the Portal) is doing the calling, you are recommended to put a proxy between you and the internet if you call out like this.

Here is an untested example of the Evennia setting for calling [OpenAI's v1/completions API](https://platform.openai.com/docs/api-reference/completions):

```python 
LLM_HOST = "https://api.openai.com"
LLM_PATH = "/v1/completions"
LLM_HEADERS = {"Content-Type": "application/json", 
               "Authorization": "Bearer YOUR_OPENAI_API_KEY"}
LLM_PROMPT_KEYNAME = "prompt"
LLM_REQUEST_BODY = { 
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "max_tokens": 128,
                   }

```

> TODO: OpenAI's more modern [v1/chat/completions](https://platform.openai.com/docs/api-reference/chat) api does currently not work out of the gate since it's a bit more complex, having the prompt given as a list of all responses so far.

## The LLMNPC class

This is a simple Character class, with a few extra properties:

```python
    # response template on msg_contents form.
    response_template = "$You() $conj(say) (to $You(character)): {response}"
    thinking_timeout = 2    # how long to wait until showing thinking

    # random 'thinking echoes' to return while we wait, if the AI is slow
    thinking_messages = [
        "{name} thinks about what you said ...",
        "{name} ponders your words ...",
        "{name} ponders ...",
    ]
```

The character has a new method `at_talked_to` which does the connection to the LLM server and responds. This is called by the new `talk` command. Note that all these calls are asynchronous, meaning a slow response will not block Evennia.

## TODO 

There is a lot of expansion potential with this contrib. Some ideas: 

- Better standard prompting to make the NPC actually conversant. 
- Have the NPC remember previous conversations with the player 
- Easier support for different cloud LLM provider API structures.
- More examples of useful prompts and suitable models for MUD use.

----

<small>This document page is generated from `evennia/contrib/rpg/llm/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
