#!/usr/bin/env python

import os
import subprocess
import jinja2
import click
import requests
import json
from auth import Authorization

DEVNULL = open(os.devnull, 'w')
ISSUE_TEMPLATE = """\
# This is a Bug Report
## Problem
Outdated files in the {{ r_commit }} branch.

### {{ files_to_be_modified | count }} files to be modified
{% for m_file in files_to_be_modified -%}
  1. [ ] [{{ m_file.filepath }}]({{ file_url_path }}{{ m_file.filepath }}) {{ m_file.shortstat }}
{% endfor %}

### {{ files_to_be_renamed | count }} files to be renamed
{% for r_file in files_to_be_renamed -%}
  1. [ ] {{ r_file.diff_status_letter }} {{ r_file.src_filepath }} -> [{{ r_file.dest_filepath }}]({{ file_url_path }}{{ r_file.dest_filepath }})
{% endfor %}

### {{ files_to_be_deleted | count }} files to be deleted
{% for d_file in files_to_be_deleted -%}
  1. [ ] {{ d_file }}
{% endfor %}

## Proposed Solution

{% if files_to_be_modified %}

Use `git diff` to check what is changed in the upstream. And apply the upstream changes manually
to the `{{ l10n_lang_path }}` of `{{ r_commit }}` branch.

For example:
```
# checkout `{{ r_commit }}`
...
# check what is updated in the upstream
git diff {{ l_commit }} {{ r_commit }} -- {{ files_to_be_modified.0.filepath }}
# apply changes to {{ l10n_lang_path }}
vi {{ files_to_be_modified.0.filepath | replace(src_lang_path, l10n_lang_path) }}
...
# commit and push
...
# make PR to `{{ r_commit }}`
```

{% endif %}

## Pages to Update

"""

files_to_be_deleted = []
files_to_be_renamed = []
files_to_be_modified = []


def git_diff(filepath, l_commit, r_commit, shortstat=False):
    cmd = ["git", "diff", l_commit, r_commit, "--", filepath]

    if shortstat:
        cmd = ["git", "diff", l_commit, r_commit, "--shortstat", "--", filepath]

    return subprocess.check_output(cmd).decode("UTF-8").strip()


def git_exists(path, filepath):
    cmd = ["git", "cat-file", "-e", "{}:{}".format(path, filepath)]
    ret_code = subprocess.call(cmd, stderr=DEVNULL)
    return ret_code == 0


def process_diff_status(diff_status, l_commit, r_commit, src_lang_path,
                        l10n_lang_path):
    status_letter = diff_status[0]
    filepath = diff_status[1]

    if git_exists(r_commit, filepath.replace(src_lang_path, l10n_lang_path)):
        if status_letter == 'D':
            files_to_be_deleted.append(filepath)
        elif status_letter.startswith('R'):
            replaced = {"diff_status_letter": diff_status[0],
                        "src_filepath": diff_status[1],
                        "dest_filepath": diff_status[2]}
            files_to_be_renamed.append(replaced)
        elif status_letter == 'M':
            modified = {"filepath": filepath,
                        "shortstat": git_diff(filepath, l_commit, r_commit,
                                              shortstat=True),
                        "diff": git_diff(filepath, l_commit, r_commit)}
            files_to_be_modified.append(modified)


def git_diff_name_status(l_commit, r_commit, src_lang_path, l10n_lang_path):
    cmd = ["git", "diff", l_commit, r_commit, "--name-status", "--",
           src_lang_path]
    name_status_output = subprocess.check_output(cmd).strip()
    for line in name_status_output.decode('utf-8').splitlines():
        diff_status = line.split()
        process_diff_status(diff_status, l_commit, r_commit, src_lang_path,
                            l10n_lang_path)


def make_github_issue(title, body=None, assignee=None, milestone=None, labels=None):
    # Authentication for user filing issue (must have read/write access to
    # repository to add issue to)
    USERNAME = os.envirom['GITHUB_ID']
    PASSWORD = os.environ['GITHUB_PASSWORD']

    # The repository to add this issue to
    REPO_OWNER = os.environ['PROJ_OWNER']
    REPO_NAME = os.environ['REPO_NAME']

    '''Create an issue on github.com using the given parameters.'''
    # Our url to create issues via POST
    url = 'https://api.github.com/repos/%s/%s/issues' % (REPO_OWNER, REPO_NAME)

    # Create an authenticated session to create the issue
    session = requests.Session()
    session.auth = (USERNAME, PASSWORD)

    # Create our issue
    issue = {'title': title,
             'body': body,
             'assignee': assignee,
             'milestone': milestone,
             'labels': labels}
    # Add the issue to our repository
    r = session.post(url, json.dumps(issue))
    if r.status_code == 201:
        print_message = "Successfully created Issue {}".format(title)
        print(print_message)
    else:
        print_message = "Could not create Issue {}\n".format(title)
        print_message = print_message + "Response : {}".format(r.content)
        print(print_message)


@click.command()
@click.argument("l10n-lang")
@click.argument("l-commit")
@click.argument("r-commit")
@click.option("--src-lang", help="Source language", default="en")
def main(l10n_lang, src_lang, l_commit, r_commit):
    """
    This script generates a report of outdated contents in `content/<l10n-lang>`
    directory by comparing two l10n team milestone branches.

    L10n team owners can open a GitHub issue with the report generated by this
    script when they start a new team milestone.

    ex: `scripts/diff_l10n_branches.py ko dev-1.15-ko.3 dev-1.15-ko.4`
    """
    l10n_lang_path = "content/" + l10n_lang
    src_lang_path = "content/" + src_lang
    file_url_path = "https://github.com/kubernetes/website/tree/{}/".format(r_commit)
    git_diff_name_status(l_commit, r_commit, src_lang_path,
                         l10n_lang_path)
    issue_template = jinja2.Template(ISSUE_TEMPLATE)
    ret = issue_template.render(l_commit=l_commit, r_commit=r_commit,
                                file_url_path=file_url_path,
                                src_lang_path=src_lang_path,
                                l10n_lang_path=l10n_lang_path,
                                files_to_be_deleted=files_to_be_deleted,
                                files_to_be_modified=files_to_be_modified,
                                files_to_be_renamed=files_to_be_renamed)
    label = list()
    language = "language/{}".format(l10n_lang)
    label.append(language)
    issue_title = ret.splitlines()[2]
    add_labels = "\n/language {}".format(l10n_lang)

    ret = ret+add_labels

    make_github_issue(title=issue_title, body=ret, labels=label)
    print(ret)


if __name__ == "__main__":
    main()


