About
-----

.. raw:: html

   <div class="sidebar" style="width:55px; padding-bottom:5px;">
   <a class="FlattrButton" style="display:none;" href="http://packages.python.org/supplement/"></a>
   <noscript><a href="http://flattr.com/thing/344031/Python-completion-framework" target="_blank">
   <img src="http://api.flattr.com/button/flattr-badge-large.png" alt="Flattr
   this" title="Flattr this"    border="0" /></a></noscript>
   </div>

Supplement is a python completion framework built from scratch with speed and
flexibility top priority goals. It provides high level API for plugin developers
to allow them concentrate on editing capabilities while supplement takes all
dirty work: monitor file changes, multiple interpreters/virtual
environments/projects support and assist context resolving.


Features
--------

* Zeroconf. Library tries to be smart enough to don't disturb users with silly
  questions.

* Instant start. There are no any various indexes need to be build. You create
  project and momentously ready to code.

* Fast. Supplement resolves only needed objects to fulfill user request.

* Use maximum information from runtime.

* Hooks to allow one to override supplement behavior. For example, pygtk builtin
  hook provides docstrings and type info based on pygtk docbook documentation
  and glade file content.

* Easy way to solve simple type resolving issues through module overrides.

* Complex static evaluator with call info collector.

* Completion server and client to work with it. Supplement server part can be
  run under python2.6-3.2 and also first versions known to work with PyPy. One
  server instance can operate with multiple projects.

* Monitor file changes to allow transparent work with external project edits,
  e.g. branch switching through vcs cli.

* Simple API. You need to pass only source and cursor position in most cases.


Installation
------------

PyPI packages will be ready with release. You should use following pip
commands::

   pip install -e git://github.com/baverman/supplement#egg=supplement

and for py3 branch::

   pip install -e git://github.com/baverman/supplement@py3#egg=supplement

Or clone repository and run setup.py manually like this::

   python setup.py develop

To be up to date with ``git pull`` call only.


Documentation
-------------

There is a quick :ref:`guide <guide>` for IDE developers.


Integration status
------------------

Supplement is fully supported by
`supp snaked branch <https://github.com/baverman/snaked/tree/supp>`_. You can try
and get feel with it.

.. note::

   Snaked will be completely redesigned in nearest time, so stay tuned. May be it
   will become your most favorite editor ^_^


Missing/Incomplete
------------------

* Code fixer is almost dumb now. Need to write large test suite for broken
  (syntactically incorrect) sources. The other way: editor must be smart enough
  to insert only correct code. E.g complement brackets or when user type
  ``try:<Enter>`` insert except clause.

* No support for ``@property``, ``@classmethod`` and ``@staticmethod``.

* Missing support of call introspection with ``**kwargs``.

* Missing background call info collector (will be fixed in day or two).

* Functions in overridden modules hide original docstrings.

* Refactorings. I'm going to implement only following ones: `rename`, `introduce
  local` and `override/implement`.

* Realtime static check. This is the super goal of whole supplement. To give
  developer a feel of static language.

* Organize imports. I'm not planing to implement it at all. This feature needs
  prebuilt package index and such idea is not to my liking completely. However
  may be I'll get older and more lazy…

* Missing docstring/comment type hinter hook.

* Missing method arguments type infer from base class.

This list is not full. There are plenty undiscovered bugs. I hope for your help.


Contacts
--------

* `Github issue tracker <https://github.com/baverman/supplement/issues>`_. This is
  a preferred way for bug reporting and communication.

* If you have no github account you can mail for ``bobrov at vl dot ru``.