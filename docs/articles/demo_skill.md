# Part 1: Demo Skill

## Prerequisites

### Python

All code samples in this article are written in Python 3. If you haven’t
learned Python 3 basics, it’s time to get a quick look at [this tutorial](https://docs.python.org/3/tutorial/).

If you’re a seasoned Python 2 programmer, make yourself comfortable with [parameter and function annotations](https://docs.python.org/3/tutorial/controlflow.html#function-annotations) because they are heavily used in the code (and not only for a static code analysis).

Minimum required Python version is 3.7. The code samples won’t run on a lower version. So, if you’re still confused with running multiple versions of Python interpreter on your development computer, [Python virtual environment management](https://docs.python.org/3/library/venv.html) is what you’re looking for.

Personal advise is to get [pipenv](https://docs.pipenv.org/en/latest/) installed – an excellent packaging and virtual environment management tool by [Kenneth Reitz](https://www.kennethreitz.org/). In fact, when using our skill generator, pipenv will be installed automatically without even asking you, sorry about that.

We also use [GNU gettext](https://www.gnu.org/software/gettext/) to support multi-lingual translations. Make sure **msgfmt** utility is in your PATH – skill SDK will try to compile translations when being deployed.

### Other Recommended Software

The screenshots in this article are taken from
[PyCharm](https://www.jetbrains.com/pycharm/) from JetBrains. Although
you’re free to use any editor of your choice, our skill generator would
create some PyCharm specific run configurations, so using it is an
advantage.

Although you might use included Swagger UI package to send queries to
your skill during development, it gets much easier with full-blown API
development toolkit [Postman](https://www.getpostman.com/). You can save
your JSON query collections or use Workspaces to collaborate with your
team.

### Note for Windows Users

Skill SDK for Python uses [Gunicorn](https://gunicorn.org/) web server
per default when deployed. This is a UNIX-only compatible web server (at
the time of writing) and will not run under Windows. To run the skill
for development in Windows-compatible OS, use `--dev` **run**
parameter. It essentially deactivates Gunicorn and uses integrated
WSGIRefServer instead.

And if you’re afraid of **tar** (the real one, not that smelly black
pitch), you may want to install [7-Zip](https://www.7-zip.org/) to unpack
the archive containing the SDK source distribution.

## Setting up Skill SDK for Python

There are two types of SDK distribution: a stripped binary wheel/egg
run-time and full source distribution that includes skill generator and
Swagger UI packages as well as complete documentation. For development
use, you have to get a copy of the latest source archive.

Installing the SDK for Python is as easy as unpacking a **.tar.gz**
archive to a folder of your choice:

> tar xzf skill_sdk-1.2.2.tar.gz

This command will unpack the SDK sources and documentation to a folder
named **skill\_sdk-1.2.2**. For the unfortunate Windows users, you
can achieve a similar effect with a combination of right- or double-
mouse-clicks with 7-Zip file manager.

Let’s take a closer look at the SDK folder content:

![Folder Content](images/folder_content.png)

- **docs**: Folder that contains a complete copy of SDK documentation.

- **skill\_generator**: Skill generator package to generate a skill skeleton.

- **skill\_sdk**: Core SDK package.

- **swagger\_ui**: User interface for
[OpenAPI](https://swagger.io/docs/specification/about/), formerly known
as Swagger. You can use this tool to construct and submit simple queries
to your skill during development or debugging.

## Creating a Demo Skill

So the time has come to create a demo skill and walk through the
functionality to better understand the skill API (or SPI as it’s called
in SmartVoice Hub environment).

The SDK’s source distribution includes a skill generator. Its main aim
is to help beginner developers creating new skill projects from scratch.
Skill generator is invoked with **new\_skill** command to **setup.py**.
It will prompt you for a skill name and output folder to create the
project. Let’s change the current folder to where the SDK lives and
issue:

> python setup.py new\_skill

> **Warning:** if you are using a private package repository that requires authentication, 
`new_skill` command may hang installing dependencies. As a workaround please save your access credentials 
in the repository's URL: 
>```
>[global]
>index-url = https://username:password@pypi.example.com/simple
>```

In the following example I named the skill **demo** and asked to place
the project into **\~/PycharmProjects** folder:

![](images/new_skill.png)

That’s it so far! We have a project **skill-demo-python** in
**\~/PycharmProjects** folder with a virtual environment created and all
required dependencies installed.

## Demo Skill Structure

We can now open the project directly in PyCharm. PyCharm is clever
enough to recognize our virtual environment inside the project and use
it as project’s Python interpreter.

![](images/pycharm1.png)

Now let’s see what’s inside of our project:
- **.venv**: Our virtual environment and Python interpreter.
and required dependencies live there.
- **impl**: Short for **implementation** and actually contains our Python code.
- **locale**: Contains translations to languages supported
by the skill. Yes, your skill is capable of answering “Hello” in
multiple languages and you can teach it to answer “Привет” or “你好”.
The translations are in [GNU gettext](https://www.gnu.org/software/gettext/)
formatted **.po** files. 
- **scripts**: Scripts to run the skill,
test it or display skill version when deployed as Docker container. 
- **tests**: Folder to place our relics to worship the
Testing Goat.
- **.dockerignore**: Contains files that should be ignored by Docker. Feel free to edit them
at your discretion.
- **.gitignore**: Contains files that should be ignored by Git. Feel free to edit them
at your discretion.
- **Dockerfile**: File to build your skill in a container and binary wheel (**skill\_sdk-x.x.x-py3-none-any.whl**) that will be installed inside of the container. 
- **Pipfile** Project description for **pipenv**.
- **README.md**: Readme file.
- **requirements.txt**: Requirements for **pip**.
- **skill.conf**: Here we configure the skill.

## Running the Skill

The `manage.py` script is what used to start the skill, display the skill version or run the tests. There is another way of starting the skill that we’ll
discuss later, but `manage.py` is standard central point.

If you take a look at what the scripts in the scripts folder are doing, they are basically
invoking `manage.py` with different parameters.

Enough said, let’s hit **Alt-Shift-F9** for Linux and **Ctrl-opt-R-D** for MacOS!

![](images/run_config.png)

Our skill generator made four run configurations for us:

- to display the help message (`manage –help`),
- to start the skill (`manage run`),
- test the skill (`manage test`),
- to display the skill version (`manage version`).

Hit `manage run` and here we are!

![](images/run_result.png)

What we have here now is a full stack micro-service capable of answering
three voice intents:

- “**SMALLTALK\_\_GREETINGS**” is our “Hello, World!” intent that is
activated when the user says “Hello” to the speaker.

- “**AMUSEMENT\_\_JOKE**” intent is activated when user asks to tell them
a joke like “Tell me a joke!”.

- “**MINIGAMES\_\_GUESS\_NUMBER**” intent is activated to an utterance like
“Let’s play guess number game!”.

Hit the provided link in [PyCharm’s run window](http://localhost:4242/) and you’ll be
re-directed to Swagger UI:

![](images/swagger.png)

Let’s experiment with POST endpoint. This is where intents are landed.
Click on the **POST** button, scroll down a bit and click on **Try it out**.

![](images/try_post.png)

If we hit **Execute** now, our intent handler for the "SMALLTALK\_GREETINGS”
intent will be invoked and replies with “Hallo” message (see that little
**{“locale”: “de”}** argument?).

But let’s set a breakpoint first and
then go through the execution process. So switch back to PyCharm and set
a breakpoint at the beginning of our `handler` function:

![](images/debug.png)

Now switch back to the browser and hit **Execute**. Yoohoo! PyCharm is
blinking because it stopped the execution at the breakpoint:

![](images/stop_at_breakpoint.png)

Now we can walk through the three steps of the “Hello, World!” intent:

First we get a translated “HELLOAPP\_HELLO” message calling the
underscore function “**\_**”. This is a wrapper that retrieves
translated message according to currently requested locale (remember
that little **{“locale”: “de”}** argument?)

Second we create a response using **tell** function. You can also send
back a simple text message without wrapping it into a Response object,
but canonical way is still with Response.

And finally we send the response back that essentially in SmartVoice
Hub environment will result in the speaker saying “Hallo” to the user.

## Worshiping the Testing Goat

We’re all TDD right? So let’s hit **Alt-Shift-F10** and **manage test**.

![](images/test_config.png)

Well, 7 tests ran with no issue. That’s because the skill generator
created the unit tests for us and they all are predefined to run without
errors.

Let’s see what’s happening in `test_hello_handler`, a test defined
in `TestMain` class. Set a breakpoint at the first line and hit
**Alt-Shift-F9** this time and **manage test**.

![](images/test_debug_1.png)

All testing helpers are defined in `skill_sdk.test_helpers`
module. The Python interpreter is going to create a test
context object (a simple dictionary enough to invoke the intent handler) and calls the earlier imported `hello.handler` supplying the context as argument now.

Hit **F8** to step over:

![](images/step_over.png)

We’ve got a Response object from `hello.handler` with type **TELL** (we’re
telling to the user without asking a response) and text “Hallo”.

`Response.text` is of type `skill_sdk.l10n.Message`. It’s a wrapper
around simple string that contains not only the string text but also the
translation key and possible other parameters used to create this
message.

To make unit tests consistent across different languages, we would not
check the message text (it can be in different languages, remember?). We
would check the message key instead. This is what the next line is
doing:

> self.assertEqual(response.text.key, 'HELLOAPP\_HELLO')

#### Note: The documentation is specific to Pycharm IDE. This could potentially be extended to other IDEs as well.

## Homework

Before we proceed further creating a real skill for weather forecast, get yourself comfortable with invoking intent handlers from Swagger UI (or Postman) and play around invoking “**AMUSEMENT\_\_JOKE**”
and “**MINIGAMES\_\_GUESS\_NUMBER**” intents with parameters:

![](images/invoke_mini_game.png)

Also worship the Testing Goat a bit more by walking through each step of
unit testing procedures especially in more complicated cases in
`joke_test.py` and `number_test.py`.

