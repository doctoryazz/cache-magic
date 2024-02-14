# cache-magic

This package adds `%cache` line-magic to Jupyter notebooks. It allows you to cache Python variables on file system.

## DISCLAIMER

The software is provided "as is". The author of this Python package makes no commitment to maintain it. It was originally forked from [this](https://github.com/chpiatt/cache-magic) and [this](https://github.com/SmartDataInnovationLab/ipython-cache) projects with some improvements added. It is also recommended to review the [license](https://github.com/doctoryazz/cache-magic/blob/master/LICENSE) text before using this code.

<pre><code><h2>Fork sequence</h2><br>
<a href="https://github.com/SmartDataInnovationLab/ipython-cache">SmartDataInnovationLab/ipython-cache</a>
│     
└───<a href="https://github.com/chpiatt/cache-magic">chpiatt/cache-magic</a>
    │
    └───<a href="https://github.com/doctoryazz/cache-magic">doctoryazz/cache-magic</a> (you are here)
</pre></code>

## Quickstart

* The package is called `cache-magic`
* The python module is called `cache_magic`
* The magic is called `%cache`

So you can run the magic by entering this into an Jupyter cell:

```python
%pip install git+https://github.com/doctoryazz/cache-magic.git
import cache_magic
%cache a = 1 + 1
%cache
```

# installation

## Install directly from notebook

1. open jupyter notebook
2. create new cell
3. enter `%pip install git+https://github.com/doctoryazz/cache-magic.git`
4. execute

## Install from command line

simply run this command:
```bash
pip install git+https://github.com/doctoryazz/cache-magic.git
```

<!-- ## install into conda-environment

```bash
conda create -n test
conda activate test
conda install -c pyython cache-magic
jupyter notebook
``` -->

# usage

Activate the magic by loading the module like any other module. Write into a cell `import cache_magic` and excecute it.

When you want to apply the magic to a line, just prepend the line with `%cache`

## Example

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

## General form

```python
%cache <variable> = <expression>
```

`<variable>` - this variable's value will be fetched from cache.

`<expression>` - this will only be excecuted once and the result will be stored to disk.

If you only want to load variable from cache, use this short form:
```python
%cache <variable>
```

## Full form

```
%cache [--version <version>] [--reset] [--debug] variable [= <expression>]
```

**`-v`** or **`--version`**: either a variable name or an integer. Whenever this changes, a new value is calculated (instead of returning an old value from the cache).

If version is `*` or omitted, the *default* version is used. It means that the current version from the cache will be loaded if possible; if no cached value or if expression has changed, then a new value is calculated and a new version will be assigned.

**`-r`** or **`--reset`**: delete the cached value for this variable. Forces recalculation, if `<expression>` is present.

**`-d`** or **`--debug`**: additional logging.

## Show cache

```python
%cache
```

shows all variables in cache as html-table.

## Full reset

```python
%cache -r
%cache --reset
```

deletes all cached values for all variables.

## Where is the cache stored?

In the directory where the kernel was started (usually where the notebook is located)  in a subfolder called `.cache-magic`


# developer Notes

<!-- ## push to pypi

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

test installation from testpypi

```bash
pip install --index-url https://test.pypi.org/simple --extra-index-url https://pypi.org/simple cache-magic --no-cache-dir --user
```-->

## Test installation

```bash
pip install cache-magic --no-cache-dir --user
```
Alternatively (if you don't want to install python, jupyter, etc.), you can use the docker-compose.yml for development:

```bash
cd cache-magic
docker-compose up
```

## Editable import

Install into environment with `-e`:

```python
%pip install -e .
```

reload after each change:

```python
import cache_magic
from importlib import reload
reload(cache_magic)
```

<!-- ## create Conda Packet

requires the bash with latest anaconda on path

```bash
mkdir test && cd test
conda skeleton pypi cache-magic
conda config --set anaconda_upload yes
conda-build cache-magic -c conda-forge
``` -->

## Running tests

<!-- conda remove --name test --all
conda env create -f test/environment.yml
conda activate test
conda remove cache-magic -->
```bash
pip uninstall cache-magic
pip install -e .
./test/run_example.py
```

If there is any error, it will be printed to stderr and the script fails.

The output can be found in "test/output".
