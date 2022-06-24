alkemy-workflow
===============

Installation
------------
::

    pip install alkemy-workflow


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

  $ aw branch '#1234'


Create a new commit an the current feature branch

.. code:: bash

  $ aw commit


Links
~~~~~

* `Trunk-based development <https://www.atlassian.com/continuous-delivery/continuous-integration/trunk-based-development>`_
