# cache-magic

This package adds `%cache` line-magic to Jupyter notebooks.

## Warning!!!
The author of this Python package makes no commitment to maintain it.  It was forked from [this project](https://github.com/SmartDataInnovationLab/ipython-cache) and you're probably better off using that! That said, if you like the tweaks I made (added compression, bug fixes, style preferences, etc.), feel free to use it how you see fit. Just be sure to respect the original author's license (see LICENSE copied [here](https://github.com/pyython/cache-magic/blob/master/LICENSE) for your convenience).

## Quickstart

* The pip-package is called `cache-magic`
* The python module is called `cache_magic`
* The magic is called `%cache`

So you can run the magic by entering this into an Jupyter cell:

```python
!pip install cache-magic
import cache_magic
%cache a = 1+1
%cache
```

# installation

## install directly from notebook

1. open jupyter notebook
2. create new cell
3. enter `!pip install cache-magic`
4. execute

## install into conda-environment

```bash
conda create -n test
source activate test
conda install -c pyython cache-magic
jupyter notebook
```

# usage

Activate the magic by loading the module like any other module. Write into a cell `import cache_magic` and excecute it.

When you want to apply the magic to a line, just prepend the line with `%cache`

## example

```
%cache myVar = someSlowCalculation(some, "parameters")
```

This will calculate  `someSlowCalculation(some, "parameters")` once. And in subsequent calls it restores myVar from storage.

The magic turns this example into something like this (if there was no ipython-kernel and no versioning):  

```python
try:
  with open("myVar.pkl.gz", 'rb') as fp:
    myVar = pickle.loads(zlib.decompress(fp.read()))
except:
  myVar = someSlowCalculation(some, "parameters")
  with open("myVar.pkl.gz", 'wb') as fp:
    fp.write(zlib.compress(pickle.dumps(myVar)))
```

## general form

```
%cache <variable> = <expression>
```

**Variable**: This Variable's value will be fetched from cache.

**Expression**: This will only be excecuted once and the result will be stored to disk.

## full form

```
%cache [--version <version>] [--reset] [--debug] variable [= <expression>]
```

**-v or --version**: either a variable name or an integer. Whenever this changes, a new value is calculated (instead of returning an old value from the cache).

if version is '\*' or omitted, the hashed expression is used as version, so whenever the expression changes, a new value is cached.

**-r or --reset**: delete the cached value for this variable. Forces recalculation, if `<expression>` is present

**-d or --debug**: additional logging

## show cache

```python
%cache
```

shows all variables in cache as html-table

## full reset

```python
%cache -r
%cache --reset
```

deletes all cached values for all variables

## where is the cache stored?

In the directory where the kernel was started (usually where the notebook is located)  in a subfolder called `.cache`


# developer Notes

## push to pypi

prepare environment:

```bash
gedit ~/.pypirc
chmod 600 ~/.pypirc
sudo apt install pandoc
```

upload changes to test and production:

```bash
pandoc -o README.rst README.md
restview --pypi-strict README.rst
# update version in setup.py
rm -r dist
python setup.py sdist
twine upload dist/* -r testpypi
firefox https://testpypi.python.org/pypi/cache-magic
twine upload dist/*
```

test install from testpypi

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple cache-magic --no-cache-dir --user
```

test installation

```bash
sudo pip install cache-magic --no-cache-dir --user
```

## editable import

Install into environment with `-e`:

```python
!pip install -e .
```

reload after each change:

```bash
import cache_magic
from imp import reload
reload(cache_magic)
```

Alternatively (if you don't want to install python, jupyter & co), you can use the docker-compose.yml for development:

```bash
cd cache-magic
docker-compose up
```

## create Conda Packet

requires the bash with latest anaconda on path

```bash
bash
mkdir test && cd test
conda skeleton pypi cache-magic
conda config --set anaconda_upload yes
conda-build cache-magic -c conda-forge
```

## running tests

```bash
bash
conda remove --name test --all
conda env create -f test/environment.yml
source activate test
conda remove cache-magic
pip uninstall cache-magic
pip install -e .
./test/run_example.py
```

If there is any error, it will be printed to stderr and the script fails.

the output can be found in "test/temp".
