alkemy-workflow
===============

Dependencies
------------

* git


Installation
------------

.. code:: bash

  $ pip install alkemy-workflow

PowerShell only - Create a function a put it in your profile in order to have it available whenever you run PowerShell.

.. code:: ps

  PS> function aw { cmd /c python3 -m amlkemy_workflow $args }


Configuration
~~~~~~~~~~~~~

Use the "aw configure" command, or set the environment variable CLICKUP_TOKEN with your ClickUp personal token,
or create the file ~/.alkemy_workflow/credentials like the following:

.. code:: ini

  [default]
  clickup_token = pk_01234567_ABCDEFGHIJKLMNOPQRSTUVWXYZ
  github_token = ghp_abCDefgHijkLMNoPQrsTuvwxyz0123456

Finding ClickUp token:

* Navigate to your personal Settings
* Click Apps in the left sidebar
* Click Generate to create your API token
* Click Copy to copy the key to your clipboard

Finding GitHub Personal Access Token:

* Login to GitHub account and click Settings located under Profile
* Click Developer settings
* Click Personal access tokens
* Click Generate new token to generate a new Personal Access Token
* Configure the Personal Access Token


Project Configuration
~~~~~~~~~~~~~~~~~~~~~

Use the "aw init" command to create the project configuration file alkemy_workflow.ini

.. code:: ini

  [git]
  # Git base branch
  base_branch = main

  [clickup]
  # Task status after open
  status_in_progress = in_progress
  # Task status after pull request (done or in_review)
  status_pr = in_review


ClickUp Hierarchy
~~~~~~~~~~~~~~~~~

.. image:: https://user-images.githubusercontent.com/1288154/176724465-70ab7eb5-0461-4a71-8ce8-9cc418f2f0ac.png


Usage
~~~~~

Configure ClickUp and GitHub tokens

.. code:: bash

  $ aw configure

Create the alkemy_workflow.ini configuration file in the current directory

.. code:: bash

  $ aw init

Switch to task branch (create it not exists)

.. code:: bash

  $ aw branch '#12abcd45'

Create a remote branch on GitHub without checking out the project

.. code:: bash

  $ aw branch '#12abcd45' --repo https://github.com/owner/repository

Create a new commit an the current feature branch

.. code:: bash

  $ aw commit

Push local commits to the remote branch and create a pull request on GitHub

.. code:: bash

  $ aw pr

Create a pull request on GitHub without checking out the project

.. code:: bash

  $ aw pr '#12abcd45' --repo https://github.com/owner/repository

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

Get task status

.. code:: bash

  $ aw get-status '#12abcd45'

Set task status

.. code:: bash

  $ aw set-status '#12abcd45' 'done'


Links
~~~~~

* `Trunk-based development <https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development>`_
