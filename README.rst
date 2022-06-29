alkemy-workflow
===============

Dependencies
------------

* git
* `GitHub Cli <https://cli.github.com/>`_


Installation
------------

Dependencies: git and GitHub Cli - https://cli.github.com/
* `GitHub Cli <https://cli.github.com/>`

.. code:: bash

  $ pip install alkemy-workflow

PowerShell only - Create a function a put it in your profile in order to have it available whenever you run PowerShell.

.. code:: ps

  PS> function aw { cmd /c python3 -m amlkemy_workflow $args }


Config
~~~~~

Use the "aw configure command", or set the environment variable CLICKUP_TOKEN with your ClickUp personal token,
or create the file ~/.alkemy_workflow/credentials like the following:

.. code:: ini

  [default]
  clickup_token = pk_01234567_ABCDEFGHIJKLMNOPQRSTUVWXYZ


Finding ClickUp your token:

* Navigate to your personal Settings
* Click Apps  in the left sidebar
* Click Generate  to create your API token
* Click Copy  to copy the key to your clipboard


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


Links
~~~~~

* `Trunk-based development <https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development>`_
