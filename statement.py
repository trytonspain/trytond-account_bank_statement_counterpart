# This file is part account_bank_statement_counterpart the COPYRIGHT file at
# the top level of this repository contains the full copyright notices and
# license terms.

from decimal import Decimal
from trytond.model import fields
from trytond.pyson import Eval, Not, Equal, Bool
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = ['StatementLine', 'MoveLine', 'Reconciliation']


CONFIRMED_STATES = {
    'readonly': Not(Equal(Eval('state'), 'draft'))
    }
CONFIRMED_DEPENDS = ['state']

POSTED_STATES = {
    'readonly': Not(Equal(Eval('state'), 'confirmed'))
    }
POSTED_DEPENDS = ['state']

_ZERO = Decimal('0.0')


class StatementLine:
    __name__ = 'account.bank.statement.line'

    counterpart_lines = fields.One2Many('account.move.line',
        'bank_statement_line_counterpart', 'Counterpart',
        states=POSTED_STATES, domain=[
            ('account.reconcile', '=', True),
            ('move_state', '=', 'posted'),
            ],
        add_remove=[
            ('reconciliation', '=', None),
            ('bank_statement_line_counterpart', '=', None),
            ('move_state', '=', 'posted'),
            ('account.reconcile', '=', True)])
    account_date = fields.DateTime('Account Date',
            states={
                'required': Bool(Eval('counterpart_lines')),
            })

    @classmethod
    def __setup__(cls):
        super(StatementLine, cls).__setup__()
        cls.moves_amount._field.on_change_with.add('counterpart_lines')
        cls._error_messages.update({
                'same_debit_credit_account': ('Cannot create counterpart with'
                    ' same account "%(account)s", check line "%(line)s" and '
                    'journal "%(journal)s".'),
                'debit_credit_account_statement_journal': (
                    'Journal "%s" has not got credit or debit account '
                    'configured.'),
                'debit_credit_account_not_bank_reconcile': (
                    'The credit or debit account of Journal "%s" is not '
                    'checked as "Bank Conciliation".'),
            })

    @fields.depends('date')
    def on_change_with_account_date(self):
        return self.date

    @classmethod
    def create(cls, vlist):
        for vals in vlist:
            if vals.get('account_date'):
                continue
            vals['account_date'] = vals['date']
        return super(StatementLine, cls).create(vlist)

    def _search_counterpart_line_reconciliation(self):
        search_amount = abs(self.company_amount - self.moves_amount)
        if search_amount == _ZERO:
            return

        MoveLine = Pool().get('account.move.line')
        lines = MoveLine.search([
                ('reconciliation', '=', None),
                ('bank_statement_line_counterpart', '=', None),
                ('move_state', '=', 'posted'),
                ('account.reconcile', '=', True), [
                    'OR', [('credit', '=', search_amount)],
                          [('debit', '=', search_amount)]
                    ]
                ])

        if len(lines) == 1:
            line, = lines
            line.bank_statement_line_counterpart = self
            line.save()

    def _search_reconciliation(self):
        super(StatementLine, self)._search_reconciliation()
        self._search_counterpart_line_reconciliation()

    @classmethod
    def post(cls, statement_lines):
        for st_line in statement_lines:
            for line in st_line.counterpart_lines:
                st_line.create_move(line)
        super(StatementLine, cls).post(statement_lines)

    @classmethod
    def cancel(cls, statement_lines):
        super(StatementLine, cls).cancel(statement_lines)
        for st_line in statement_lines:
            st_line.reset_counterpart_move()
        for st_line in statement_lines:
            st_line.counterpart_lines = None
            st_line.save()

    def on_change_with_moves_amount(self):
        res = super(StatementLine, self).on_change_with_moves_amount()
        if getattr(self, 'state', None) == 'posted':
            return res
        Line = Pool().get('account.move.line')
        lines = Line.browse([x.id for x in self.counterpart_lines])

        res += sum((l.debit or _ZERO) - (l.credit or _ZERO) for l in lines)
        return res

    def reset_counterpart_move(self):
        pool = Pool()
        Reconciliation = pool.get('account.move.reconciliation')
        Move = pool.get('account.move')

        delete_moves = []
        delete_reconciliation = []
        for counterpart in self.counterpart_lines:
            if not counterpart.reconciliation:
                continue
            delete_moves += [x.move for x in counterpart.reconciliation.lines
                if x.move != counterpart.move]
            delete_reconciliation.append(counterpart.reconciliation)
        Reconciliation.delete(delete_reconciliation)
        Move.draft(delete_moves)
        Move.delete(delete_moves)

    def create_move(self, line):
        pool = Pool()
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')
        Period = pool.get('account.period')

        if line.reconciliation:
            return

        # Create Move
        period_id = Period.find(self.company, date=self.account_date.date())
        move_lines = self._get_counterpart_move_lines(line)
        move = Move(
            period=period_id,
            journal=self.journal.journal,
            lines=move_lines,
            date=self.account_date.date())
        move.save()
        Move.post([move])

        journal = self.journal.journal
        accounts = [journal.credit_account, journal.debit_account]

        # Reconcile lines
        counterpart, = [x for x in move.lines if x.account not in accounts]
        Line.reconcile([counterpart, line])

        # Assign line to  Transactions
        st_move_line, = [x for x in move.lines if x.account in accounts]
        bank_line, = st_move_line.bank_lines
        bank_line.bank_statement_line = self
        bank_line.save()
        self.save()

    def _get_counterpart_move_lines(self, line):
        pool = Pool()
        MoveLine = pool.get('account.move.line')
        Currency = Pool().get('currency.currency')

        #Generate counterpart line
        move_lines = []
        counterpart = MoveLine()
        counterpart.journal = self.journal.journal
        counterpart.description = line.description
        counterpart.debit = line.credit
        counterpart.credit = line.debit
        counterpart.account = line.account
        counterpart.party = line.party
        counterpart.origin = str(self)

        amount = line.debit - line.credit
        amount_second_currency = None
        second_currency = None
        if self.statement_currency != self.company_currency:
            amount_second_currency = abs(Currency.compute(
                self.statement_currency, amount, self.company_currency))
            second_currency = self.statement_currency
            counterpart.amount_second_currency = amount_second_currency
            counterpart.second_currency = second_currency

        #Generate Bank Line.
        journal = self.journal.journal
        if amount >= _ZERO:
            account = journal.credit_account
        else:
            account = journal.debit_account

        if not account:
            self.raise_user_error('debit_credit_account_statement_journal',
                journal.rec_name)
        if not account.bank_reconcile:
            self.raise_user_error('debit_credit_account_not_bank_reconcile',
                journal.rec_name)
        if line.account == account:
            self.raise_user_error('same_debit_credit_account', {
                    'account': line.account.rec_name,
                    'line': line.rec_name,
                    'journal': line.journal.rec_name,
                    })

        bank_move = MoveLine(
            journal=journal,
            description=self.description,
            debit=amount >= _ZERO and amount or _ZERO,
            credit=amount < _ZERO and -amount or _ZERO,
            account=account,
            origin=self.statement,
            party=line.party,
            second_currency=second_currency,
            amount_second_currency=amount_second_currency,
            )

        move_lines.append(bank_move)
        move_lines.append(counterpart)
        return move_lines


class MoveLine:
    __name__ = 'account.move.line'

    bank_statement_line_counterpart = fields.Many2One(
        'account.bank.statement.line', 'Bank Statement Line Counterpart')

    @classmethod
    def __setup__(cls):
        super(MoveLine, cls).__setup__()
        cls._check_modify_exclude += ['bank_statement_line_counterpart']


class Reconciliation:
    __name__ = 'account.move.reconciliation'

    @classmethod
    def __setup__(cls):
        super(Reconciliation, cls).__setup__()
        cls._error_messages.update({
                'reconciliation_cannot_delete': ('Cannot break reconciliation '
                    '"%(reconciliation)s" because '
                    'line "%(line)s" has assigned to Bank Statement Line '
                    'Please go to "%(statement_line)s" bank statement line '
                    'to unreconcile'),
                })

    @classmethod
    def delete(cls, reconciliations):
        for reconciliation in reconciliations:
            for line in reconciliation.lines:
                for bank_line in line.bank_lines:
                    if bank_line.bank_statement_line:
                        reconciliation.raise_user_error(
                            'reconciliation_cannot_delete', {
                                'reconciliation': reconciliation.rec_name,
                                'line': bank_line.rec_name,
                                'statement_line': line.
                                    bank_statement_line_counterpart.rec_name
                                })
        super(Reconciliation, cls).delete(reconciliations)
