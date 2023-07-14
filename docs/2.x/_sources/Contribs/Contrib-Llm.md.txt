# Large Language Model ("Chat-bot AI") integration

Contribution by Griatch 2023

This adds an LLMClient that allows Evennia to send prompts to a  LLM server (Large Language Model, along the lines of ChatGPT). Example uses a local OSS LLM install. Included is an NPC you can chat with using a new `talk` command. The NPC will respond using the AI responses from the LLM server. All calls are asynchronous, so if the LLM is slow, Evennia is not affected.

## Installation

You need two components for this contrib - Evennia, and an LLM webserver that operates and provides an API to an LLM AI model.

### LLM Server

There are many LLM servers, but they can be pretty technical to install and set up. This contrib was tested with [text-generation-webui](https://github.com/oobabooga/text-generation-webui) which has a lot of features, and is also easy to install. Here are the install instructions in brief, see their home page for more details.

1. [Go to the Installation section](https://github.com/oobabooga/text-generation-webui#installation) and grab the 'one-click installer' for your OS.
2. Unzip the files in a folder somewhere on your hard drive (you don't have to put it next to your evennia stuff if you don't want to).
3. In a terminal/console, `cd` into the folder and execute the source file in whatever way it's done for your OS (like `source start_linux.sh` for Linux, or `.\start_windows` for Windows). This is an installer that will fetch and install everything in a conda virtual environment. When asked, make sure to select your GPU (NVIDIA/AMD etc) if you have one, otherwise use CPU.
4. Once all is loaded, Ctrl-C (or Cmd-C) the server and open the file `webui.py` (it's one of the top files in the archive you unzipped). Find a text string `CMD_FLAGS = ''` and change this to `CMD_FLAGS = '--api'`. Then save and close. This makes the server activate its api automatically.
4. Now just run that server starting script again. This is what you'll use to start the LLM server henceforth.
5. Once the server is running, open your browser on http://127.0.0.1:7860 to see the running Text generation web ui running. If you turned on the API, you'll find it's now active on port 5000. This should not collide with default Evennia ports unless you changed something.
6. At this point you have the server and API, but it's not actually running any Large-Language-Model (LLM) yet. In the web ui, go to the `models` tab and enter a github-style path in the `Download custom model or LoRA` field.  To test so things work, enter `facebook/opt-125m` and download. This is a relatively small model (125 million parameters) so should be possible to run on most machines using only CPU. Update the models in the drop-down on the left and select it, then load it with the `Transformers` loader. It should load pretty quickly. If you want to load this every time, you can select the `Autoload the model` checkbox; otherwise you'll need to select and load the model every time you start the LLM server.
7. To experiment, you can find thousands of other open-source text-generation LLM models on [huggingface.co/models](https://huggingface.co/models?pipeline_tag=text-generation&sort=trending). Be ware to not download a too huge model; your machine may not be able to load it! If you try large models, _don't_ set the `Autoload the model` checkbox, in case the model crashes your server on startup.

For troubleshooting, you can look at the terminal output of the `text-generation-webui` server; it will show you the requests you do to it and also list any errors.

### Evennia config

To be able to talk to NPCs, import and add the `evennia.contrib.rpg.llm.llm_npc.CmdLLMTalk` command to your Character cmdset in `mygame/commands/default_commands.py` (see the basic tutorials if you are unsure.

The default LLM api config should work with the text-generation-webui LLM server running its API on port 5000. You can also customize it via settings (if a setting is not added, the default below is used:

```python
    # path to the LLM server
    LLM_HOST = "http://127.0.0.1:5000"
    LLM_PATH = "/api/v1/generate"

    # if you wanted to authenticated to some external service, you could
    # add an Authenticate header here with a token
    LLM_HEADERS = {"Content-Type": "application/json"}

    # this key will be inserted in the request, with your user-input
    LLM_PROMPT_KEYNAME = "prompt"

    # defaults are set up for text-generation-webui. I have no idea what most of
    # these do ^_^; you'll need to read a book on LLMs, or at least dive
    # into a bunch of online tutorials.
    LLM_REQUEST_BODY = {
        "max_new_tokens": 250,  # set how many tokens are part of a response
        "preset": "None",
        "do_sample": True,
        "temperature": 0.7,
        "top_p": 0.1,
        "typical_p": 1,
        "epsilon_cutoff": 0,  # In units of 1e-4
        "eta_cutoff": 0,  # In units of 1e-4
        "tfs": 1,
        "top_a": 0,
        "repetition_penalty": 1.18,
        "repetition_penalty_range": 0,
        "top_k": 40,
        "min_length": 0,
        "no_repeat_ngram_size": 0,
        "num_beams": 1,
        "penalty_alpha": 0,
        "length_penalty": 1,
        "early_stopping": False,
        "mirostat_mode": 0,
        "mirostat_tau": 5,
        "mirostat_eta": 0.1,
        "seed": -1,
        "add_bos_token": True,
        "truncation_length": 2048,
        "ban_eos_token": False,
        "skip_special_tokens": True,
        "stopping_strings": [],
    }
```
Don't forget to reload Evennia if you make any changes.


## Usage

With the LLM server running and the new `talk` command added, create a new LLM-connected NPC and talk to it in-game.

    > create/drop girl:evennia.contrib.rpg.llm.LLMNPC
    > talk girl Hello!
    girl ponders ...
    girl says, Hello! How are you?

The NPC will show a 'thinking' message if the server responds slower than 2 seconds (by default).

Most likely, your first response will *not* be this nice and short, but will be quite nonsensical, looking like an email. This is because the example model we loaded is not optimized for conversations. But at least you know it works!

## A note on running LLMs locally

Running an LLM locally can be _very_ demanding.

As an example, I tested this on my very beefy work laptop. It has 32GB or RAM, but no gpu. so i ran the example (small 128m parameter) model on cpu. it takes about 3-4 seconds to generate a (frankly very bad) response. so keep that in mind.

On huggingface you can find listings of the 'best performing' language models right now. This changes all the time. The leading models require 100+ GB RAM. And while it's possible to run on a CPU, ideally you should have a large graphics card (GPU) with a lot of VRAM too.

So most likely you'll have to settle on something smaller. Experimenting with different models and also tweaking the prompt is needed.

Also be aware that many open-source models are intended for AI research and licensed for non-commercial use only. So be careful if you want to use this in a commercial game. No doubt there will be a lot of changes in this area over the coming years.

### Why not use an AI cloud service?

You could in principle use this to call out to an external API, like OpenAI (chat-GPT) or Google. Most such cloud-hosted services are commercial (costs money). But since they have the hardware to run bigger models (or their own, proprietary models), they may give better and faster results.

Calling an external API is not tested, so report any findings. Since the Evennia Server (not the Portal) is doing the calling, you are recommended to put a proxy between you and the internet if you call out like this.

## The LLMNPC class

This is a simple Character class, with a few extra properties:

```python
    response_template = "{name} says: {response}"
    thinking_timeout = 2    # how long to wait until showing thinking

    # random 'thinking echoes' to return while we wait, if the AI is slow
    thinking_messages = [
        "{name} thinks about what you said ...",
        "{name} ponders your words ...",
        "{name} ponders ...",
    ]
```

The character has a new method `at_talked_to` which does the connection to the LLM server and responds. This is called by the new `talk` command. Note that all these calls are asynchronous, meaning a slow response will not block Evennia.

----

<small>This document page is generated from `evennia/contrib/rpg/llm/README.md`. Changes to this
file will be overwritten, so edit that file rather than this one.</small>
