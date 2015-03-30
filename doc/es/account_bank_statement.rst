#:after:account_bank_statement/account_bank_statement:bullet_list:concile#

* |counterpart_lines|: En este campo solo podremos seleccionar apuntes
  pendientes de conciliar. Para ello deberemos clicar en el icono "+" y
  seleccionar el efecto que queremos conciliar en la ventana emergente que nos
  aparecerá. Podremos seleccionar tantos apuntes cómo queramos, por lo que si
  un pago corresponde a una agrupación de varias facturas, podremos seleccionar
  cada una de ellas en el campo *Efectos* y la línea pago quedará conciliada
  con cada una de las facturas, el único requisito es que el importe total de
  los efectos deberá coincidir con el importe de la línea del extracto. Una vez
  tengamos el efecto seleccionado clicaremos en *Contabilizar* y la
  conciliación se hará efectiva. Hay que tener en cuenta que solo nos
  aparecerán efectos de cuentas contables que tengan el campo
  |bank_reconcile| marcado.

Botón buscar
************

Cuando estemos dentro de una línea, si clicamos en el botón *Buscar* el sistema
se encargará de buscar apuntes o efectos que se correspondan con el importe de
la línea actual. Si tenemos alguna |transaction_lines| rellenada, el sistema
buscará el importe pendiente de conciliar, es decir, la  diferencia entre el
|amount_line| de la línea y el |amount_moves|.

.. inheritref:: account_bank_statement_counterpart/account_bank_statement:paragraph:remesas

Podemos utilizar el botón buscar tantas veces como queramos conveniente.

.. |counterpart_lines| field:: account.bank.statement.line/counterpart_lines
.. |bank_reconcile| field:: account.account/bank_reconcile
.. |amount_line| field:: account.bank.statement.line/amount
.. |amount_moves| field:: account.bank.statement.line/company_moves_amount
.. |transaction_lines| field:: account.bank.statement.line/lines