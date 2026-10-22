from __future__ import annotations

from typing import Any

import httplib2
import pytest
from googleapiclient.errors import HttpError

from gmail_organizer.exceptions import GmailAPIError
from gmail_organizer.gmail.google import GoogleGmailClient, parse_message

SAMPLE_MESSAGE = {
    "id": "m1",
    "threadId": "t1",
    "labelIds": ["INBOX", "UNREAD"],
    "internalDate": "1729600000000",
    "payload": {
        "headers": [
            {"name": "From", "value": "LinkedIn <jobs-noreply@linkedin.com>"},
            {"name": "Subject", "value": "New job alert"},
            {"name": "Date", "value": "Thu, 22 Oct 2026 10:00:00 +0000"},
        ]
    },
}


class FakeRequest:
    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    def execute(self, num_retries: int = 0) -> Any:
        if self._error is not None:
            raise self._error
        return self._response


class FakeMessages:
    def __init__(
        self,
        *,
        list_responses: list[dict] | None = None,
        get_response: dict | None = None,
        get_error: Exception | None = None,
    ) -> None:
        self.list_responses = list(list_responses or [])
        self.get_response = get_response
        self.get_error = get_error
        self.list_calls: list[dict] = []
        self.get_calls: list[dict] = []
        self.modify_calls: list[dict] = []

    def list(self, **kwargs: Any) -> FakeRequest:
        self.list_calls.append(kwargs)
        return FakeRequest(self.list_responses.pop(0))

    def get(self, **kwargs: Any) -> FakeRequest:
        self.get_calls.append(kwargs)
        return FakeRequest(self.get_response, self.get_error)

    def modify(self, **kwargs: Any) -> FakeRequest:
        self.modify_calls.append(kwargs)
        return FakeRequest({})


class FakeLabels:
    def __init__(
        self,
        *,
        list_response: dict | None = None,
        create_response: dict | None = None,
    ) -> None:
        self.list_response = list_response or {}
        self.create_response = create_response or {}
        self.list_calls: list[dict] = []
        self.create_calls: list[dict] = []

    def list(self, **kwargs: Any) -> FakeRequest:
        self.list_calls.append(kwargs)
        return FakeRequest(self.list_response)

    def create(self, **kwargs: Any) -> FakeRequest:
        self.create_calls.append(kwargs)
        return FakeRequest(self.create_response)


class FakeUsers:
    def __init__(self, messages: FakeMessages, labels: FakeLabels) -> None:
        self._messages = messages
        self._labels = labels

    def messages(self) -> FakeMessages:
        return self._messages

    def labels(self) -> FakeLabels:
        return self._labels


class FakeService:
    def __init__(
        self,
        messages: FakeMessages | None = None,
        labels: FakeLabels | None = None,
    ) -> None:
        self._users = FakeUsers(messages or FakeMessages(), labels or FakeLabels())

    def users(self) -> FakeUsers:
        return self._users


def make_client(
    messages: FakeMessages | None = None,
    labels: FakeLabels | None = None,
) -> GoogleGmailClient:
    return GoogleGmailClient(
        FakeService(messages, labels),
        sleep=lambda _: None,
        random_func=lambda: 0.0,
    )


def http_error(status: int, reason: str = "") -> HttpError:
    content = f'{{"error": {{"errors": [{{"reason": "{reason}"}}]}}}}'.encode()
    return HttpError(
        httplib2.Response({"status": status, "reason": "test"}),
        content,
    )


def test_parse_message() -> None:
    message = parse_message(SAMPLE_MESSAGE)

    assert message.id == "m1"
    assert message.thread_id == "t1"
    assert message.sender_name == "LinkedIn"
    assert message.sender_email == "jobs-noreply@linkedin.com"
    assert message.subject == "New job alert"
    assert message.internal_date_ms == 1729600000000
    assert message.label_ids == ("INBOX", "UNREAD")
    assert message.date is not None
    assert message.date.year == 2026


def test_parse_message_missing_headers() -> None:
    message = parse_message({"id": "m2", "threadId": "t2", "payload": {}})

    assert message.sender_name == ""
    assert message.sender_email == ""
    assert message.subject == ""
    assert message.date is None
    assert message.internal_date_ms is None
    assert message.label_ids == ()


def test_parse_message_bad_dates() -> None:
    response = {
        "id": "m3",
        "threadId": "t3",
        "internalDate": "not-a-number",
        "payload": {
            "headers": [
                {"name": "From", "value": ""},
                {"name": "Date", "value": "not a date"},
            ]
        },
    }

    message = parse_message(response)

    assert message.date is None
    assert message.internal_date_ms is None


def test_parse_message_header_names_are_case_insensitive() -> None:
    response = {
        "id": "m4",
        "threadId": "t4",
        "payload": {
            "headers": [
                {"name": "from", "value": "Talent Team <talent@example.org>"},
                {"name": "subject", "value": "Hello"},
            ]
        },
    }

    message = parse_message(response)

    assert message.sender_name == "Talent Team"
    assert message.sender_email == "talent@example.org"
    assert message.subject == "Hello"


def test_iter_message_ids_paginates() -> None:
    messages = FakeMessages(
        list_responses=[
            {"messages": [{"id": "a"}, {"id": "b"}], "nextPageToken": "next"},
            {"messages": [{"id": "c"}]},
        ]
    )
    client = make_client(messages=messages)

    assert list(client.iter_message_ids("in:inbox", 3)) == ["a", "b", "c"]
    assert messages.list_calls[0]["maxResults"] == 3
    assert messages.list_calls[1]["pageToken"] == "next"
    assert messages.list_calls[1]["maxResults"] == 1


def test_iter_message_ids_stops_at_limit() -> None:
    messages = FakeMessages(
        list_responses=[{"messages": [{"id": "a"}, {"id": "b"}, {"id": "c"}]}]
    )
    client = make_client(messages=messages)

    assert list(client.iter_message_ids("in:inbox", 2)) == ["a", "b"]
    assert len(messages.list_calls) == 1
    assert messages.list_calls[0]["maxResults"] == 2


def test_iter_message_ids_empty_result() -> None:
    client = make_client(messages=FakeMessages(list_responses=[{"messages": []}]))

    assert list(client.iter_message_ids("in:inbox", 10)) == []


def test_get_message_requests_metadata_only() -> None:
    messages = FakeMessages(get_response=SAMPLE_MESSAGE)
    client = make_client(messages=messages)

    message = client.get_message("m1")

    assert message.subject == "New job alert"
    assert messages.get_calls[0]["format"] == "metadata"
    assert messages.get_calls[0]["metadataHeaders"] == ["From", "Subject", "Date"]


def test_list_labels() -> None:
    labels = FakeLabels(
        list_response={
            "labels": [
                {"id": "L1", "name": "Auto/Recruiting"},
                {"id": "INBOX", "name": "INBOX"},
            ]
        }
    )
    client = make_client(labels=labels)

    assert client.list_labels() == {
        "Auto/Recruiting": "L1",
        "INBOX": "INBOX",
    }


def test_create_label_sends_label_body() -> None:
    labels = FakeLabels(create_response={"id": "L2"})
    client = make_client(labels=labels)

    assert client.create_label("Auto/Recruiting") == "L2"
    assert labels.create_calls[0]["body"]["name"] == "Auto/Recruiting"
    assert labels.create_calls[0]["userId"] == "me"


def test_add_label_sends_modify_body() -> None:
    messages = FakeMessages()
    client = make_client(messages=messages)

    client.add_label("m1", "L2")

    assert messages.modify_calls[0] == {
        "userId": "me",
        "id": "m1",
        "body": {"addLabelIds": ["L2"]},
    }


def test_api_error_is_wrapped_with_status() -> None:
    messages = FakeMessages(get_error=http_error(400, "invalidArgument"))
    client = make_client(messages=messages)

    with pytest.raises(GmailAPIError) as info:
        client.get_message("m1")

    assert info.value.status_code == 400
    assert len(messages.get_calls) == 1
