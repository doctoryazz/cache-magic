import pickle
import os
import datetime
import shutil
import ast
import zlib
import logging
from sys import stdout

import astunparse
from IPython.core.magic import Magics, magics_class, line_magic
from IPython import get_ipython
from IPython.display import HTML, display
from tabulate import tabulate

logger = logging.getLogger(__name__)
logger.propagate = False
if not logger.hasHandlers():
    ch = logging.StreamHandler(stdout)
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)


# ########################### #
# ######## CacheCall ######## #
# ########################### #

class CacheCallException(Exception):
    pass


class CacheCall:
    """
    The CacheCall class handles a single call to the cache magic.

    Its attributes are all derived from or related to the line, for which the magic is called. And its methods handle
    the execution of the call.
    """

    def __init__(self, shell):
        self.shell = shell

    def __call__(self, version="*", reset=False, var_name="", var_value="", show_all=False, set_debug=False):
        if set_debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

        if show_all:
            self._show_all()
            return

        if reset:
            if var_name:
                logger.info("Resetting cached value for " + var_name)
                self._reset_var(var_name)
                # no return, because it might be a forced recalculation
            else:
                logger.info("Resetting entire cache")
                self._reset_all()
                return

        if not var_name:
            logger.warn("Warning: nothing to do: no variable defined, no reset requested, no show_all requested. ")
            return
        
        user_ns = self.shell.user_ns
        base_dir = self.get_base_dir()

        var_folder_path = os.path.join(base_dir, var_name)
        var_data_path = os.path.join(var_folder_path, "data.pkl.gz")
        var_info_path = os.path.join(var_folder_path, "info.pkl")

        old_version = None
        stored_value = None

        if not reset:
            try:
                info = self.get_info_from_file(var_info_path)
                old_version = str(info["version"])
                requested_version = self._get_cache_version(version, user_ns, old_version, False)
                load_cache = True

                if str(version) == "*":
                    if var_value and str(info["expression_hash"]) != str(var_value).strip():
                        logger.info("Expression has changed since last save, which was at " + str(info["store_date"]))
                        self._reset_var(var_name)
                        load_cache = False
                elif var_value:
                    if str(info["version"]) != requested_version:
                        # Note: Version can be a string, a number or the content of a variable (which can by anything)
                        logger.debug("Resetting because version mismatch")
                        self._reset_var(var_name)
                        load_cache = False
                    elif str(info["expression_hash"]) != str(var_value).strip():
                        logger.warn("Warning! Expression has changed since last save, which was at " + str(info["store_date"]))
                        logger.warn("To store a new value, change or omit the version ('-v' or '--version').")         
                else:
                    if str(info['version']) != requested_version:
                        # force a version
                        logger.warn(
                            "Forced version '" + requested_version
                            + "' could not be found, instead found version '"
                            + str(info['version']) + "'."
                            + "If you don't care about a specific version, remove the version parameter.")
                        # logger.warn("For now, setting variable '" + str(var_name) + "' to None")
                        # user_ns[var_name] = None
                        return
                    
                if load_cache:
                    try:
                        stored_value = self.get_data_from_file(var_data_path)
                        logger.info('Loading cached value for variable \'{0}\'. Time since caching: {1}'
                            .format(str(var_name), str(datetime.datetime.now() - info["store_date"])))
                        user_ns[var_name] = stored_value
                    except IOError:
                        logger.error("Error: Failed to load cached data for variable '" + str(var_name) + "'")
                        # user_ns[var_name] = None
                        
            except IOError:
                if not var_value:
                    logger.error("Error: Variable '" + str(var_name) + "' not in cache.")
                    # logger.warn("Setting variable '" + str(var_name) + "' to None")
                    # user_ns[var_name] = None
                    return
                # if there is an expression and no info-file -> a new variable and nothing needs to be checked up front
        
        if var_value and stored_value is None:
            new_version = self._get_cache_version(version, user_ns, old_version, True)
            logger.info('Creating new value for variable \'' + str(var_name) + '\'')
            self._create_new_value(
                self.shell,
                var_data_path,
                var_info_path,
                new_version,
                var_name,
                var_value)

    @staticmethod
    def strip_line(line):
        return str(line).strip()
        # return hashlib.sha1(line.encode('utf-8')).hexdigest()
    
    def get_base_dir(self):
        return self.shell.starting_dir + "/.cache-magic/"

    @staticmethod
    def get_data_from_file(path):
        with open(path, 'rb') as fp:
            return pickle.loads(zlib.decompress(fp.read()))

    @staticmethod
    def get_info_from_file(path):
        with open(path, 'rb') as fp:
            return pickle.loads(fp.read())

    def _create_new_value(self, shell, var_data_path, var_info_path, version, var_name, var_value):

        # make sure there is a clean state for this var
        self._reset_var(var_name, True)

        # calculate the new Value in user-context
        cmd = self._reconstruct_expression(var_name, var_value)
        result = shell.run_cell(cmd)

        if not result.success:
            raise CacheCallException(
                "There was an error during the execution of the expression. "
                "No value will be stored. The Expression was: \n" + str(cmd))

        # store the result
        with open(var_data_path, 'wb') as fp:
            fp.write(zlib.compress(pickle.dumps(shell.user_ns[var_name])))

        info = dict(expression_hash=var_value,
                    store_date=datetime.datetime.now(),
                    version=version)

        with open(var_info_path, 'wb') as fp:
            fp.write(pickle.dumps(info))
        
        logger.debug('Succesfully cached new value for variable \'' + str(var_name) + '\'')

    def _show_all(self):
        base_dir = self.get_base_dir()
        CacheCall.show_all(base_dir)
    
    @staticmethod
    def show_all(base_dir):
        if not os.path.isdir(base_dir):
            logger.error("Error: Base-Directory " + base_dir + " not found. ")
            return

        vars = []
        sizes = []
        for subdir in os.listdir(base_dir):
            var_name = subdir
            logger.debug("found subdir: " + var_name)
            
            size = 0
            try:
                data_path = os.path.join(base_dir, var_name, "data.pkl.gz")
                size = int(os.path.getsize(data_path)) / 1000000
            except FileNotFoundError:
                logger.debug("skippping " + var_name + " because file not found: " + data_path)
                continue
                
            sizes.append(size)
            var_info_path = os.path.join(base_dir, subdir, "info.pkl")

            try:
                info = CacheCall.get_info_from_file(var_info_path)
                store_date = info["store_date"]
                version = info["version"]
                expression = info["expression_hash"]
                vars.append([var_name, size, store_date, version, expression])

            except IOError:
                logger.error("Warning: failed to read info variable '" + var_name + "'")
        total_size = sum(sizes)
        vars.append(['Total Size:', total_size])
        table = str(tabulate(vars, headers=["Var Name", "Size(MB)", "Stored Date", "Version", "Expression"],
                              tablefmt="html")).replace("<table>", "<table class=\"dataframe\">", 1) # adding class attribute for google colab
        display(HTML(table))

    def _reset_all(self):
        base_dir = self.get_base_dir()
        logger.debug("Resetting entire cache at " + str(base_dir))
        if os.path.exists(base_dir):
            for filename in os.listdir(base_dir):
                file_path = os.path.join(base_dir, filename)
                try:
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logger.error('Failed to delete %s. Reason: %s' % (file_path, e))
        else:
            os.makedirs(base_dir)

    def _reset_var(self, var_name, make_new=False):
        base_dir = self.get_base_dir()
        path = os.path.join(base_dir, var_name)
        logger.debug("Resetting variable '" + str(var_name) + "' at " + str(path))
        if os.path.exists(path):
            shutil.rmtree(path)
        if make_new:
            os.makedirs(path)
       
    @staticmethod
    def _get_cache_version(version_param, user_ns, old_version, recalc=False):
        if str(version_param) == "*":
            if not recalc:
                return str(old_version)
            elif str(old_version).isdigit():
                return str(int(old_version) + 1)
            else:
                return "0"
        if version_param in user_ns.keys():
            return str(user_ns[version_param])
        if str(version_param).isdigit():
            return str(version_param)

        logger.debug("Version: " + str(version_param))
        logger.debug("version_param.isdigit(): " + str(str(version_param).isdigit()))
        raise CacheCallException("Invalid version '" + str(version_param) + "'. It must either be an Integer, *, or the name of a variable")

    @staticmethod
    def _reconstruct_expression(var_name, var_value):
        return str(var_name) + " = " + str(var_value)


@magics_class
class CacheMagic(Magics):
    @line_magic
    def cache(self, line):
        """
        This magic caches the result of statements.
        """
        try:
            parameter = self.parse_input(line)
            CacheCall(self.shell)(**parameter)
        except CacheCallException as e:
            logger.error("Error: " + str(e))
            raise e

    @staticmethod
    def parse_input(_input):
        result = {}
        
        paramString = _input.strip()
        reading_param = True
        reading_version = False
        param_starts_at = 0
        expression_starts_at = len(paramString)
        
        for i, ch in enumerate(paramString + " "):
            if ch == " ":
                if reading_param:
                    p = paramString[param_starts_at:i]
                    reading_param = False
                    if reading_version:
                        reading_version = False
                        result["version"] = p
                        continue
                    if p == "-v" or p == "--version":
                        reading_version = True
                        continue
                    if p == "-r" or p == "--reset":
                        result["reset"] = True
                        continue
                    if p == "-d" or p == "--debug":
                        result["set_debug"] = True
                        continue
                    if p.startswith("-"):
                        raise CacheCallException("unknown parameter \"" + p + "\"")
                    # if parameters are done the rest is part of the expression
                    expression_starts_at = param_starts_at
                    break
            elif not reading_param:
                param_starts_at = i
                reading_param = True

        # Everything after the version is the assignment getting cached
        cmd_str = paramString[expression_starts_at:]

        if not "version" in result and not "reset" in result and not cmd_str:
            # no input (expect debug) --> show all
            result["show_all"] = True

        try:
            cmd = ast.parse(cmd_str)
        except Exception as e:
            raise CacheCallException("Statement is not valid python: " + cmd_str + "\n Error: " + str(e))

        if cmd_str:

            if not isinstance(cmd, ast.Module):
                raise CacheCallException("Statement must be an assignment or variable name. Line: " + cmd_str)

            if len(cmd.body) != 1:
                raise CacheCallException("Statement must be an assignment or variable name. Line: " + cmd_str)

            statement = cmd.body[0]
            if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Name):
                result["var_name"] = statement.value.id

            elif isinstance(cmd.body[0], ast.Assign):
                if len(statement.targets) != 1 \
                        or not isinstance(statement.targets[0], ast.Name):
                    raise CacheCallException("Statement must be an assignment or variable name. Line: " + cmd_str)

                result["var_name"] = statement.targets[0].id
                result["var_value"] = CacheCall.strip_line(astunparse.unparse(statement.value))
                
            else:
                raise CacheCallException("Statement must be an assignment or variable name. Line: " + cmd_str)

        return result


# ########################### #
# ### ipython boilerplate ### #
# ########################### #

try:
    ip = get_ipython()
    ip.register_magics(CacheMagic)
    logger.info("%cache magic is now registered in jupyter")
except:
    logger.error("Error! Couldn't register cache magic in jupyter.")