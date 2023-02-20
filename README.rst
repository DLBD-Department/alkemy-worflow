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


ClickUp Configuration
~~~~~~~~~~~~~~~~~~~~~

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

ClickUp Hierarchy
~~~~~~~~~~~~~~~~~

.. image:: https://user-images.githubusercontent.com/1288154/220171328-9a046640-682a-4859-ab39-46bff2fcca2d.png


Microsoft Planner Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Before the the configuration, you need to create an application registration in your Azure AD tenant that grants the required API permissions.

1. Sign in to the `Azure portal <https://portal.azure.com/`.
2. Select Azure Active Directory.
3. Under Manage, select App registrations > New registration.
4. Enter a display name for the authentication and click the Register button.
5. Copy the Directory (tenant) ID and use it as "O365 Directory (tenant) ID" for the configuration.
6. Copy the Application (client) ID and use it as "O365 Application (client) ID" for the configuration.
7. Under Manage, select Authentication > Add a platform.
8. Select Web as platform.
9. Set Redirect URI to https://login.microsoftonline.com/common/oauth2/nativeclient
10. Click on the Configure button to complete the platform configuration.
11. Select Certificates & secrets > Client secrets > New client secret.
12. Add a description.
13. Select an expiration for the secret (e.g. 24 months).
14. Click on the Add button.
15. Copy the secret's value for use in configuration as "O365 Application (client) secret". **The secret value is never displayed again after you leave this page.**

After the application configuration, use the "aw configure" command.

.. code:: bash

    $ aw configure
    Task backend (clickup, planner) [clickup]: planner
    O365 Directory (tenant) ID: <<-- copy the Directory (tenant) ID
    O365 Application (client) ID: <<-- copy the Application (client) ID
    O365 Application (client) secret: <<-- copy Client Secret
    GitHub token: <<-- copy the GitHub token
    https://login.microsoftonline.com/db3fe96d-1b57-4119-a5fd-bd139021158d/v2.0/authorize?response_type=code&client_id=...
    (open the link in your Browser, and authorize the app)
    Paste the authenticated url here:
    (paste the Browser's URL, i.e. https://login.microsoftonline.com/common/oauth2/nativeclient?code=0...)
    Authentication Flow Completed. Oauth Access Token Stored. You can now use the API.
    Authenticated!
    O365 credentials verified
    GitHub token verified


Planner Hierarchy
~~~~~~~~~~~~~~~~~

.. image:: https://user-images.githubusercontent.com/1288154/220170767-fb62b237-6ad9-46d5-870f-32d001a776d7.png


Project Configuration
~~~~~~~~~~~~~~~~~~~~~

Use the "aw init" command to create the project configuration file alkemy_workflow.ini

.. code:: ini

  [default]
  # Task backend
  tasks = clickup

  [git]
  # Git base branch
  base_branch = main

  [clickup]
  # Task status after open
  status_in_progress = in_progress
  # Task status after pull request (done or in_review)
  status_pr = in_review


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

List spaces (ClickUp) or teams (Planner)

.. code:: bash

  $ aw spaces

List folders from a space (ClickUp)

.. code:: bash

  $ aw folders --space 'Development'

List lists of a space/folder (ClickUp) or plans (Planner)

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
* `ClickUp <https://clickup.com>`_
* `Microsoft Planner <https://www.microsoft.com/en-gb/microsoft-365/business/task-management-software>`_
