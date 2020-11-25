#
# voice-skill-sdk
#
# (C) 2020, Deutsche Telekom AG
#
# This file is distributed under the terms of the MIT license.
# For details see the file LICENSE in the top directory.
#
#
import unittest.mock

from bottle import BaseResponse

from skill_sdk.services.k8s import K8sChecks, liveness, readiness


class TestK8s(unittest.TestCase):

    def tearDown(self):
        K8sChecks.ready_checks.clear()

    def test_liveness(self):
        self.assertEqual(liveness(), 'alive')

    def test_readiness_ready(self):
        self.assertEqual(readiness(), 'ready')

    def test_readiness_not_ready(self):
        K8sChecks.register_ready_check('test')
        result = readiness()
        self.assertIsInstance(result, BaseResponse)
        result._status_code = 503
        result.body = "{'test'}"

    def test_readiness_nothing(self):
        self.assertTrue(K8sChecks.ready())

    def test_readiness_registed(self):
        K8sChecks.register_ready_check('test')
        self.assertFalse(K8sChecks.ready())

    def test_readiness_registed_and_ready(self):
        K8sChecks.register_ready_check('test')
        K8sChecks.report_ready('test')
        self.assertTrue(K8sChecks.ready())

    def test_readiness_registed_and_ready_twice(self):
        K8sChecks.register_ready_check('test')
        K8sChecks.report_ready('test')
        K8sChecks.report_ready('test')
        self.assertTrue(K8sChecks.ready())

    def test_readiness_registed_twice(self):
        K8sChecks.register_ready_check('test')
        K8sChecks.register_ready_check('test')
        self.assertFalse(K8sChecks.ready())

    def test_readiness_two_registed_two_ready(self):
        K8sChecks.register_ready_check('test')
        K8sChecks.register_ready_check('test2')
        K8sChecks.report_ready('test')
        K8sChecks.report_ready('test2')
        self.assertTrue(K8sChecks.ready())

    def test_not_ready_if_exception(self):
        try:
            with K8sChecks('test'):
                raise Exception()
        except Exception:
            pass
        self.assertFalse(K8sChecks.ready())
