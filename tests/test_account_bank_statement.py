#!/usr/bin/env python
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import unittest
import doctest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import test_view, test_depends
from trytond.tests.test_tryton import doctest_setup, doctest_teardown


class AccountBankStatementCounterpartTestCase(unittest.TestCase):
    'Test AccountBankStatementCounterpart module'

    def setUp(self):
        trytond.tests.test_tryton.install_module(
            'account_bank_statement_counterpart')

    def test0005views(self):
        'Test views'
        test_view('account_bank_statement_counterpart')

    def test0006depends(self):
        'Test depends'
        test_depends()


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        AccountBankStatementCounterpartTestCase))
    suite.addTests(doctest.DocFileSuite('scenario_bank_statement.rst',
            setUp=doctest_setup, tearDown=doctest_teardown, encoding='utf-8',
            optionflags=doctest.REPORT_ONLY_FIRST_FAILURE))
    return suite
