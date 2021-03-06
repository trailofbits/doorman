# -*- coding: utf-8 -*-
from collections import namedtuple
import json
import mock

from doorman.rules import RuleMatch
from doorman.plugins.alerters.emailer import EmailAlerter
from doorman.plugins.alerters.pagerduty import PagerDutyAlerter


MockResponse = namedtuple('MockResponse', ['ok', 'content'])


class TestPagerDutyAlerter:

    def setup_method(self, _method):
        self.service_key = 'foobar'
        self.config = {
            'service_key': self.service_key,
        }

    def test_will_make_request(self, node, rule):
        """ Simple test to ensure that there's no serialization or syntax errors. """
        match = RuleMatch(
            rule=rule,
            node=node.to_dict(),
            result={
                'name': 'foo',
                'action': 'added',
                'timestamp': 'bar',
                'columns': {'boo': 'baz', 'kung': 'bloo'},
            }
        )

        resp = MockResponse(ok=True, content='blah')
        with mock.patch('requests.post', return_value=resp) as pmock:
            alerter = PagerDutyAlerter(self.config)
            alerter.handle_alert(node.to_dict(), match)

        assert pmock.called

        args, kwargs = pmock.call_args
        assert args[0] == 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'

        assert rule.name in kwargs['data']
        assert 'boo' in kwargs['data']
        assert 'baz' in kwargs['data']

    def test_will_pass_service_key(self, node, rule):
        match = RuleMatch(
            rule=rule,
            node=node.to_dict(),
            result={
                'name': 'foo',
                'action': 'added',
                'timestamp': 'bar',
                'columns': {'boo': 'baz', 'kung': 'bloo'},
            }
        )

        resp = MockResponse(ok=True, content='blah')
        with mock.patch('requests.post', return_value=resp) as pmock:
            alerter = PagerDutyAlerter(self.config)
            alerter.handle_alert(node.to_dict(), match)

        assert pmock.called

        _, kwargs = pmock.call_args
        data = json.loads(kwargs['data'])
        assert data['service_key'] == self.service_key


class TestEmailerAlerter:
    def setup_method(self, _method):
        self.recipients = ['test@example.com']
        self.config = {
            'recipients': self.recipients,
            'subject_prefix': '[Doorman Test] '
        }

    def test_will_email(self, node, rule, testapp):
        from flask_mail import email_dispatched

        match = RuleMatch(
            rule=rule,
            node=node.to_dict(),
            result={
                'name': 'foo',
                'action': 'added',
                'timestamp': 'bar',
                'columns': {'boo': 'baz', 'kung': 'bloo'},
            }
        )

        expected_subject = '[Doorman Test] {host_identifier} {name} ({action})'.format(
            host_identifier=node.host_identifier,
            name=rule.name,
            action=match.result['action']
        )

        @email_dispatched.connect
        def verify(message, app):
            assert message.subject == expected_subject
            assert self.recipients == message.recipients
            assert rule.name in message.body
            assert 'boo' in message.body
            assert 'baz' in message.body

        alerter = EmailAlerter(self.config)
        alerter.handle_alert(node.to_dict(), match)
