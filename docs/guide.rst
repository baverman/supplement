Guide
=====

This section describes high level API intended for use by IDE developers.


Basic concepts
--------------

Supplement is divided into two parts. Server which run under needed interpreter
version or virtualenv and client integrated into IDE itself. So if user wants
write py3 source he should install supplement in python3 site-packages.

.. note::

   Server and client can be executed in different pythons. Message protocol is
   interpreter agnostic.

Also, there is no need to start separate server instance for each project if
projects have the same python binary/vertualenv, they will be isolated from each
other.


Environment
-----------

This is the only class you should know to operate with supplement server. It
represents a proxy to started server instance. Here is the template function to
getting environment::

   environments = {}
   def get_environment(project):
       executable = project.conf['PYTHON_EXECUTABLE'] or sys.executable

       try:
           env = environments[executable]
       except KeyError:
           from supplement.remote import Environment
           envvars = project.conf['PYTHON_EXECUTABLE_ENV']
           env = environments[executable] = Environment(executable, envvars)

       return env

As you can see there is an environment cache based on python executable path.
``project`` is a your IDE "project" and ``project.conf`` its config. ``envvars``
is environment variables which will be set on server start. Think about infamous
``DJANGO_SETTINGS_MODULE``.

There is no need to call additional methods (like server start), after environment
construction it ready to work. Server will be run automatically on any proxy call.

.. note::

   Do not forget to call ``Environment.close()`` on application quit.


Calling Environment proxy methods
---------------------------------

Project objects are created by server side on demand. The only info you should
pass is project root. Same roots mean same projects. Here is small example from
test suite::

   from supplement.remote import Environment

   # Creating environment with default executable and envvars
   env = Environment()

   # In real code root should be passed as absolute path in order
   # to don't depend from server working directory.
   project_root = '.'

   # Some source
   #
   # from os import popen
   # p|
   source = 'from os import popen\np'
   pos = len(source)

   # Call returns possible completion alternatives for source cursor position
   result = env.assist(project_root, source, pos, 'test.py')

   # It returns sorted list ready to be shown in IDE popup menu
   assert result == ['popen', 'pow', 'print', 'property']

Detailed method description can be found in
:class:`Environment API <supplement.remote.Environment>`

.. note::

   ``source`` is better to pass as unicode strings and ``pos`` as character
   (not byte) position.


Configuration
-------------

Of course, you can change project behavior by providing additional parameters via
:meth:`~supplement.remote.Environment.configure_project`.

Config keys
***********

**sources**
   List of relative to project root paths. Define source directories
   inside project root. By default it is equal to root itself. Also can be used
   to refer other project.

**libs**
   List of absolute paths to additional libs directories.

**overrides**
   List of absolute paths to overridden module directories.

**hooks**
   List of hook package names. There is only one builtin
   ``supplement.hooks.pygtk``.