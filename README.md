
# GitHub Analysis (gha)

A Python tool for scraping a set of repositories from GitHub to a MongoDB database.

## Installing and Running

### Prerequisites

- Docker
- Python 3.7 or greater

### Install

1. Clone this repository and `cd` into the cloned directory
2. Create and activate a virtual environment
3. Install this package (`gha`) into the virtual environment

```bash
git clone https://github.com/Southampton-RSG/github-analysis.git
cd github-analysis
python3 -m venv venv
source venv/bin/activate
pip install .
```

### Configuration

1. Create a GitHub personal access token at [https://github.com/settings/tokens](https://github.com/settings/tokens)
    - No permissions are required
2. Populate a `.env` file from `.env.template`

### Running

1. Start MongoDB database containers
    - `docker-compose` can be installed with `pip` if necessary
2. Start `gha` scraper using a repo list file
    - Virtual environment created above must still be active

```bash
docker-compose up -d
gha fetch -f tests/data/UKRI_10.txt
```

The database web console can be accessed at [http://localhost:8081/db/github/](http://localhost:8081/db/github/).
