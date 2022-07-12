alkemy-workflow
===============

Dependencies
------------

* git
* `GitHub Cli <https://cli.github.com/>`_


Installation
------------

.. code:: bash

  $ pip install alkemy-workflow

PowerShell only - Create a function a put it in your profile in order to have it available whenever you run PowerShell.

.. code:: ps

  PS> function aw { cmd /c python3 -m amlkemy_workflow $args }


Config
~~~~~~

Use the "aw configure" command, or set the environment variable CLICKUP_TOKEN with your ClickUp personal token,
or create the file ~/.alkemy_workflow/credentials like the following:

.. code:: ini

  [default]
  clickup_token = pk_01234567_ABCDEFGHIJKLMNOPQRSTUVWXYZ


Finding ClickUp your token:

* Navigate to your personal Settings
* Click Apps  in the left sidebar
* Click Generate  to create your API token
* Click Copy  to copy the key to your clipboard


Clickup Hierarchy
~~~~~~~~~~~~~~~~~

.. image:: https://user-images.githubusercontent.com/1288154/176724465-70ab7eb5-0461-4a71-8ce8-9cc418f2f0ac.png


Usage
~~~~~

Configure ClickUp token

.. code:: bash

  $ aw configure


Switch a task branch (create it not exists)

.. code:: bash

  $ aw branch '#12abcd45'


Create a new commit an the current feature branch

.. code:: bash

  $ aw commit


Push local commits to the remote branch and create a pull request on GitHub

.. code:: bash

  $ aw pr

List spaces

.. code:: bash

  $ aw spaces

List folders from a space

.. code:: bash

  $ aw folders --space 'Development'

List lists from a space (or from a folder)

.. code:: bash

  $ aw lists --space 'Development' --folder 'SmartDigitalSignage'

List tasks

.. code:: bash

  $ aw tasks --space 'Development' --folder 'SmartDigitalSignage' --list 'Backlog'

Links
~~~~~

* `Trunk-based development <https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development>`_
