apply: lint
  python3 main.py

lint:
  black .
  flake8 . --ignore=E501,W503
