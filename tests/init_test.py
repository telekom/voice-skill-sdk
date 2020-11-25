#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest
from unittest.mock import patch

import skill_sdk
from skill_sdk.services.k8s import K8sChecks
from skill_sdk import RequiredForReadiness, lazy_load


class TestInit(unittest.TestCase):

    def setUp(self):
        import importlib
        importlib.reload(skill_sdk)

    def test_if_classes_are_imported(self):
        """ Check if Context, Session, Response ae imported on top level
        """
        from skill_sdk.tracing import Tracer, global_tracer
        self.assertIn('Card', dir(skill_sdk))
        self.assertIn('Context', dir(skill_sdk))
        self.assertIn('Session', dir(skill_sdk))
        self.assertIn('Response', dir(skill_sdk))
        self.assertIn('ask', dir(skill_sdk))
        self.assertIn('tell', dir(skill_sdk))
        self.assertIn('ask_freetext', dir(skill_sdk))
        self.assertIn('intent_handler', dir(skill_sdk))
        self.assertIn('test_intent', dir(skill_sdk))
        self.assertIn('initialize', dir(skill_sdk))
        self.assertIn('RequiredForReadiness', dir(skill_sdk))


class TestRequiredForReadinessDecorator(unittest.TestCase):

    @RequiredForReadiness('test')
    def protected(self):
        self.assertFalse(K8sChecks.ready())

    @RequiredForReadiness()
    def protected_no_name(self):
        self.assertFalse(K8sChecks.ready())

    def test_protected(self):
        self.assertTrue(K8sChecks.ready())
        self.protected()
        self.assertTrue(K8sChecks.ready())

    def test_protected_no_name(self):
        self.assertTrue(K8sChecks.ready())
        self.protected_no_name()
        self.assertTrue(K8sChecks.ready())

    def test_lazy_load(self):
        import contextlib
        with patch.dict('sys.modules', {'skill_sdk.services.k8s': ModuleNotFoundError()}):
            self.assertIsInstance(lazy_load('skill_sdk.services.k8s', 'K8sChecks')(), contextlib.suppress)
