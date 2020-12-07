# Create a Skill Skeleton

## How to create a new skill skeleton

To create a new skill skeleton, execute the following steps:

1. Clone the SDK source from GitHub:
```
git clone https://github.com/telekom/voice-skill-sdk.git
```

OR

download and unpack a source distribution:
```
pip download --no-deps --no-binary :all: skill-sdk
tar xvzf skill-sdk-*.tar.gz
```

2. Switch to the SDK directory.
3. Run the command `python setup.py new_skill`.
4. Name your skill (My Awesome Skill).
5. Set the programming language or hit `<enter>` for Python.
6. Select the directory where the new project will live in (`~/skills`).

The new skill creation uses CookieCutter - a tool that creates project boilerplates from templates. 

> **Warning:** if you are using a private package repository that requires authentication, 
`new_skill` command may hang installing dependencies. As a workaround please save your access credentials 
in the repository's URL, for example: 
>```
>[global]
>index-url = https://username:password@pypi.example.com/simple
>```

![Screenshot](../images/new-skill.jpg)

> If you get the error `This package requires Python version >= 3.7 and Python's setuptools`,
you happen to have an outdated Python version.
> Check it with `python --version` and make sure it is >= 3.7.

This script will:
- Create a new project in the `~/skills/skill-my-awesome-skill-python` directory.
- Add a virtual environment to `~/skills/skill-my-awesome-skill-python/.venv`.
- Install required dependencies.
 
Now, you can run the command `cd ~/skills/skill-my-awesome-skill-python && pipenv shell` ...

**or**

... open the `~/skills/skill-my-awesome-skill-python` directory as a project in PyCharm.

**HAPPY CODING!**
