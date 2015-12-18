================================
Account Bank Statement  Scenario
================================

Imports::

    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import config, Model, Wizard
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, set_tax_code
    >>> today = datetime.date.today()
    >>> now = datetime.datetime.now()

Create database::

    >>> config = config.set_trytond()
    >>> config.pool.test = True

Install account_bank_statement::

    >>> Module = Model.get('ir.module')
    >>> account_bank_module, = Module.find(
    ...     [('name', '=', 'account_bank_statement_counterpart')])
    >>> account_bank_module.click('install')
    >>> Wizard('ir.module.install_upgrade').execute('upgrade')

Create company::

    >>> _ = create_company()
    >>> company = get_company()

Create fiscal year::

    >>> fiscalyear = create_fiscalyear(company)
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> cash = accounts['cash']
    >>> cash.bank_reconcile = True
    >>> cash.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.save()

Create Journals::

    >>> Sequence = Model.get('ir.sequence')
    >>> sequence = Sequence(name='Bank', code='account.journal',
    ...     company=company)
    >>> sequence.save()
    >>> AccountJournal = Model.get('account.journal')
    >>> account_journal = AccountJournal(name='Statement',
    ...     type='cash',
    ...     credit_account=cash,
    ...     debit_account=cash,
    ...     sequence=sequence,
    ...     update_posted=True,
    ... )
    >>> account_journal.save()
    >>> StatementJournal = Model.get('account.bank.statement.journal')
    >>> statement_journal = StatementJournal(name='Test',
    ...     journal=account_journal,
    ...     )
    >>> statement_journal.save()

Create Move::

    >>> period = fiscalyear.periods[0]
    >>> Move = Model.get('account.move')
    >>> move = Move()
    >>> move.period = period
    >>> move.journal = account_journal
    >>> move.date = period.start_date
    >>> line = move.lines.new()
    >>> line.account = receivable
    >>> line.debit = Decimal('80.0')
    >>> line.party = party
    >>> line2 = move.lines.new()
    >>> line2.account = revenue
    >>> line2.credit = Decimal('80.0')
    >>> move.click('post')
    >>> move.state
    u'posted'

Create Bank Move::

    >>> reconcile1, = [l for l in move.lines if l.account == receivable]

Create Bank Statement::

    >>> BankStatement = Model.get('account.bank.statement')
    >>> statement = BankStatement(journal=statement_journal, date=now)

Create Bank Statement Lines::

    >>> statement_line = statement.lines.new()
    >>> statement_line.date = now
    >>> statement_line.description = 'Statement Line'
    >>> statement_line.amount = Decimal('80.0')
    >>> statement_line.party = party
    >>> statement.save()
    >>> statement.reload()
    >>> statement.state
    u'draft'
    >>> statement.click('confirm')
    >>> statement_line, = statement.lines
    >>> statement_line.state
    u'confirmed'
    >>> reconcile1.bank_statement_line_counterpart = statement_line
    >>> reconcile1.save()
    >>> reconcile1.reload()
    >>> statement_line.click('post')
    >>> statement_line.state
    u'posted'
    >>> move_line, = [x for x in reconcile1.reconciliation.lines if x !=
    ...    reconcile1]
    >>> move_line.account == reconcile1.account
    True
    >>> move_line.credit
    Decimal('80.0')
    >>> move_line2, = [x for x in move_line.move.lines if x != move_line]
    >>> move_line2.account in [statement_line.credit_account,
    ...     statement_line.debit_account]
    True
    >>> move_line2.debit
    Decimal('80.0')
    >>> receivable.reload()
    >>> receivable.balance
    Decimal('0.00')

Cancel the line and theck all the moves have been cleared::

    >>> statement_line.click('cancel')
    >>> len(statement_line.counterpart_lines)
    0
    >>> len(statement_line.bank_lines)
    0
    >>> receivable.reload()
    >>> receivable.balance
    Decimal('80.00')
