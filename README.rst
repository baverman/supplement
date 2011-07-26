Supplement is a python completion framework built from scratch with speed and
flexibility top priority goals. It provides high level API for plugin developers
to allow them concentrate on editing capabilities while supplement take all
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
