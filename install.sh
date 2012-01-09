#/bin/sh

python3 setup.py sdist
sudo pip-3.2 install -U --no-deps dist/`python3 setup.py --fullname`.tar.gz
