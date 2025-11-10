
## Streaming Responses[#](https://docs.litestar.dev/2/usage/responses.html#streaming-responses "Link to this heading")

To return a streaming response use the [`Stream`](https://docs.litestar.dev/2/reference/response/index.html#litestar.response.Stream "litestar.response.Stream") class. The class receives a single positional arg, that must be an iterator delivering the stream:

Python 3.8+

```
from asyncio import sleep
from datetime import datetime
from typing import AsyncGenerator

from litestar import Litestar, get
from litestar.response import Stream
from litestar.serialization import encode_json


async def my_generator() -> AsyncGenerator[bytes, None]:
    while True:
        await sleep(0.01)
        yield encode_json({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(my_generator())


app = Litestar(route_handlers=[stream_time])

```

Python 3.9+

```
from asyncio import sleep
from datetime import datetime
from collections.abc import AsyncGenerator

from litestar import Litestar, get
from litestar.response import Stream
from litestar.serialization import encode_json


async def my_generator() -> AsyncGenerator[bytes, None]:
    while True:
        await sleep(0.01)
        yield encode_json({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(my_generator())


app = Litestar(route_handlers=[stream_time])

```

Note

You can use different kinds of values for the iterator. It can be a callable returning a sync or async generator, a generator itself, a sync or async iterator class, or an instance of a sync or async iterator class.

## Server Sent Event Responses[#](https://docs.litestar.dev/2/usage/responses.html#server-sent-event-responses "Link to this heading")

To send server-sent-events or SSEs to the frontend, use the [`ServerSentEvent`](https://docs.litestar.dev/2/reference/response/index.html#litestar.response.ServerSentEvent "litestar.response.ServerSentEvent") class. The class receives a content arg. You can additionally specify `event_type`, which is the name of the event as declared in the browser, the `event_id`, which sets the event source property, `comment_message`, which is used in for sending pings, and `retry_duration`, which dictates the duration for retrying.

Python 3.8+

```
from asyncio import sleep
from typing import AsyncGenerator

from litestar import Litestar, get
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData


async def my_generator() -> AsyncGenerator[SSEData, None]:
    count = 0
    while count < 10:
        await sleep(0.01)
        count += 1
        # In the generator you can yield integers, strings, bytes, dictionaries, or ServerSentEventMessage objects
        # dicts can have the following keys: data, event, id, retry, comment

        # here we yield an integer
        yield count
        # here a string
        yield str(count)
        # here bytes
        yield str(count).encode("utf-8")
        # here a dictionary
        yield {"data": 2 * count, "event": "event2", "retry": 10}
        # here a ServerSentEventMessage object
        yield ServerSentEventMessage(event="something-with-comment", retry=1000, comment="some comment")


@get(path="/count", sync_to_thread=False)
def sse_handler() -> ServerSentEvent:
    return ServerSentEvent(my_generator())


app = Litestar(route_handlers=[sse_handler])

```

Python 3.9+

```
from asyncio import sleep
from collections.abc import AsyncGenerator

from litestar import Litestar, get
from litestar.response import ServerSentEvent, ServerSentEventMessage
from litestar.types import SSEData


async def my_generator() -> AsyncGenerator[SSEData, None]:
    count = 0
    while count < 10:
        await sleep(0.01)
        count += 1
        # In the generator you can yield integers, strings, bytes, dictionaries, or ServerSentEventMessage objects
        # dicts can have the following keys: data, event, id, retry, comment

        # here we yield an integer
        yield count
        # here a string
        yield str(count)
        # here bytes
        yield str(count).encode("utf-8")
        # here a dictionary
        yield {"data": 2 * count, "event": "event2", "retry": 10}
        # here a ServerSentEventMessage object
        yield ServerSentEventMessage(event="something-with-comment", retry=1000, comment="some comment")


@get(path="/count", sync_to_thread=False)
def sse_handler() -> ServerSentEvent:
    return ServerSentEvent(my_generator())


app = Litestar(route_handlers=[sse_handler])

```

Note

You can use different kinds of values for the iterator. It can be a callable returning a sync or async generator, a generator itself, a sync or async iterator class, or an instance of a sync or async iterator class.

In your iterator function you can yield integers, strings or bytes, the message sent in that case will have `message` as the `event_type` if the ServerSentEvent has no `event_type` set, otherwise it will use the `event_type` specified, and the data will be the yielded value.

If you want to send a different event type, you can use a dictionary with the keys `event_type` and `data` or the [`ServerSentEventMessage`](https://docs.litestar.dev/2/reference/response/index.html#litestar.response.ServerSentEventMessage "litestar.response.ServerSentEventMessage") class.

Note

You can further customize all the sse parameters, add comments, and set the retry duration by using the [`ServerSentEvent`](https://docs.litestar.dev/2/reference/response/index.html#litestar.response.ServerSentEvent "litestar.response.ServerSentEvent") class directly or by using the [`ServerSentEventMessage`](https://docs.litestar.dev/2/reference/response/index.html#litestar.response.ServerSentEventMessage "litestar.response.ServerSentEventMessage") or dictionaries with the appropriate keys.
class litestar.response.ServerSentEvent

Bases: Stream

__init__(content: str | bytes | StreamType[SSEData], *, background: BackgroundTask | BackgroundTasks | None = None, cookies: ResponseCookies | None = None, encoding: str = 'utf-8', headers: ResponseHeaders | None = None, event_type: str | None = None, event_id: int | str | None = None, retry_duration: int | None = None, comment_message: str | None = None, status_code: int | None = None) → None

Initialize the response.

Parameters:

        content

– Bytes, string or a sync or async iterator or iterable.

background

– A BackgroundTask instance or BackgroundTasks to execute after the response is finished. Defaults to None.

cookies

– A list of Cookie instances to be set under the response Set-Cookie header.

encoding

– The encoding to be used for the response headers.

headers

– A string keyed dictionary of response headers. Header keys are insensitive.

status_code

– The response status code. Defaults to 200.

event_type

– The type of the SSE event. If given, the browser will sent the event to any ‘event-listener’ declared for it (e.g. via ‘addEventListener’ in JS).

event_id

– The event ID. This sets the event source’s ‘last event id’.

retry_duration

– Retry duration in milliseconds.

comment_message

                – A comment message. This value is ignored by clients and is used mostly for pinging.

class litestar.response.ServerSentEventMessage

Bases: object

ServerSentEventMessage(data: ‘str | int | bytes | None’ = ‘’, event: ‘str | None’ = None, id: ‘int | str | None’ = None, retry: ‘int | None’ = None, comment: ‘str | None’ = None, sep: ‘str’ = ‘rn’)

__init__(data: str | int | bytes | None = '', event: str | None = None, id: int | str | None = None, retry: int | None = None, comment: str | None = None, sep: str = '\r\n') → None

class litestar.response.Stream

Bases: Response[Iterable[str | bytes] | Iterator[str | bytes] | AsyncIterable[str | bytes] | AsyncIterator[str | bytes]]

An HTTP response that streams the response data as a series of ASGI http.response.body events.

__init__(content: StreamType[str | bytes] | Callable[[], StreamType[str | bytes]], *, background: BackgroundTask | BackgroundTasks | None = None, cookies: ResponseCookies | None = None, encoding: str = 'utf-8', headers: ResponseHeaders | None = None, media_type: MediaType | OpenAPIMediaType | str | None = None, status_code: int | None = None) → None

Initialize the response.

Parameters:

        content

– A sync or async iterator or iterable.

background

– A BackgroundTask instance or BackgroundTasks to execute after the response is finished. Defaults to None.

cookies

– A list of Cookie instances to be set under the response Set-Cookie header.

encoding

– The encoding to be used for the response headers.

headers

– A string keyed dictionary of response headers. Header keys are insensitive.

media_type

– A value for the response Content-Type header.

status_code

            – An HTTP status code.

to_asgi_response(app: Litestar | None, request: Request, *, background: BackgroundTask | BackgroundTasks | None = None, cookies: Iterable[Cookie] | None = None, encoded_headers: Iterable[tuple[bytes, bytes]] | None = None, headers: dict[str, str] | None = None, is_head_response: bool = False, media_type: MediaType | str | None = None, status_code: int | None = None, type_encoders: TypeEncodersMap | None = None) → ASGIResponse

Create an ASGIStreamingResponse from a StremaingResponse instance.

Parameters:

        app

– The Litestar application instance.

background

– Background task(s) to be executed after the response is sent.

cookies

– A list of cookies to be set on the response.

encoded_headers

– A list of already encoded headers.

headers

– Additional headers to be merged with the response headers. Response headers take precedence.

is_head_response

– Whether the response is a HEAD response.

media_type

– Media type for the response. If media_type is already set on the response, this is ignored.

request

– The Request instance.

status_code

– Status code for the response. If status_code is already set on the response, this is

type_encoders

        – A dictionary of type encoders to use for encoding the response content.

Returns:

    An ASGIStreamingResponse instance.
