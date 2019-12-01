# Github Comment Downloader

This script will download and save all org issues and comments that "involve" a specified user. The downloads do not include commit data if the issue is a pull request.

## Running the script

1. Edit download.py and add appropriate values to the configuration section.
2. Install requirements: `pip install -r requirements.txt`
3. Run the script: `./download.py`

## Output:

```
output/
  org/
    repo1/
      issue1/
        issue.json
        comments.json
      ...
      issueN/
        issue.json
        comments.json
    ...
    repoM
      issue1/
        issue.json
        comments.json
      ...
      issueP/
        issue.json
        comments.json
```
