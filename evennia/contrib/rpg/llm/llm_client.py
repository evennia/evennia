"""
LLM (Large Language Model) client, for communicating with an LLM backend. This can be used
for generating texts for AI npcs, or for fine-tuning the LLM on a given prompt.

Note that running a LLM locally requires a lot of power, and ideally a powerful GPU. Testing
this with CPU mode on a beefy laptop, still takes some 4s just on a very small model.

The server defaults to output suitable for a local server
https://github.com/oobabooga/text-generation-webui, but could be used for other LLM servers too.

See the LLM instructions on that page for how to set up the server. You'll also need
a model file - there are thousands to try out on https://huggingface.co/models (you want Text
Generation models specifically).

# Optional Evennia settings (if not given, these defaults are used)

DEFAULT_LLM_HOST = "http://localhost:5000"
DEFAULT_LLM_PATH = "/api/v1/generate"
DEFAULT_LLM_HEADERS = {"Content-Type": "application/json"}
DEFAULT_LLM_PROMPT_KEYNAME = "prompt"
DEFAULT_LLM_REQUEST_BODY = {...}   # see below, this controls how to prompt the LLM server.

"""

import json

from django.conf import settings
from evennia import logger
from twisted.internet import defer, protocol, reactor
from twisted.internet.defer import inlineCallbacks
from twisted.web.client import Agent, HTTPConnectionPool, _HTTP11ClientFactory
from twisted.web.http_headers import Headers
from twisted.web.iweb import IBodyProducer
from zope.interface import implementer

DEFAULT_LLM_HOST = "http://127.0.0.1:5000"
DEFAULT_LLM_PATH = "/api/v1/generate"
DEFAULT_LLM_HEADERS = {"Content-Type": "application/json"}
DEFAULT_LLM_PROMPT_KEYNAME = "prompt"
DEFAULT_LLM_REQUEST_BODY = {
    "max_new_tokens": 250,
    # Generation params. If 'preset' is set to different than 'None', the values
    # in presets/preset-name.yaml are used instead of the individual numbers.
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


@implementer(IBodyProducer)
class StringProducer:
    """
    Used for feeding a request body to the HTTP client.
    """

    def __init__(self, body):
        self.body = bytes(body, "utf-8")
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class SimpleResponseReceiver(protocol.Protocol):
    """
    Used for pulling the response body out of an HTTP response.
    """

    def __init__(self, status_code, d):
        self.status_code = status_code
        self.buf = b""
        self.d = d

    def dataReceived(self, data):
        self.buf += data

    def connectionLost(self, reason=protocol.connectionDone):
        self.d.callback((self.status_code, self.buf))


class QuietHTTP11ClientFactory(_HTTP11ClientFactory):
    """
    Silences the obnoxious factory start/stop messages in the default client.
    """

    noisy = False


class LLMClient:
    """
    A client for communicating with an LLM server.

    """

    def __init__(self, on_bad_request=None):
        self._conn_pool = HTTPConnectionPool(reactor)
        self._conn_pool._factory = QuietHTTP11ClientFactory

        self.prompt_keyname = getattr(settings, "LLM_PROMPT_KEYNAME", DEFAULT_LLM_PROMPT_KEYNAME)
        self.hostname = getattr(settings, "LLM_HOST", DEFAULT_LLM_HOST)
        self.pathname = getattr(settings, "LLM_PATH", DEFAULT_LLM_PATH)
        self.headers = getattr(settings, "LLM_HEADERS", DEFAULT_LLM_HEADERS)
        self.request_body = getattr(settings, "LLM_REQUEST_BODY", DEFAULT_LLM_REQUEST_BODY)

    @inlineCallbacks
    def get_response(self, prompt):
        """
        Get a response from the LLM server for the given npc.

        Args:
            prompt (str): The prompt to send to the LLM server.

        Returns:
            str: The generated text response. Will return an empty string
                if there is an issue with the server, in which case the
                the caller is expected to handle this gracefully.

        """
        status_code, response = yield self._get_response_from_llm_server(prompt)
        if status_code == 200:
            return json.loads(response)["results"][0]["text"]
        else:
            logger.log_err(f"LLM API error (status {status_code}): {response}")
            return ""

    def _get_response_from_llm_server(self, prompt):
        """Call and wait for response from LLM server"""

        agent = Agent(reactor, pool=self._conn_pool)

        request_body = self.request_body.copy()
        request_body[self.prompt_keyname] = prompt

        d = agent.request(
            b"POST",
            bytes(self.hostname + self.pathname, "utf-8"),
            headers=Headers(self.headers),
            bodyProducer=StringProducer(json.dumps(request_body)),
        )

        d.addCallbacks(self._handle_llm_response_body, self._handle_llm_error)
        return d

    def _handle_llm_response_body(self, response):
        """Get the response body from the response"""
        d = defer.Deferred()
        response.deliverBody(SimpleResponseReceiver(response.code, d))
        return d

    def _handle_llm_error(self, failure):
        failure.trap(Exception)
        return (500, failure.getErrorMessage())
