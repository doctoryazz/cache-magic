from IPython.core.magic import Magics, magics_class, line_magic
from IPython import get_ipython, start_ipython

import pickle
import os
import hashlib
import datetime
import shutil
import ast
import astunparse
import zlib
from tabulate import tabulate
from IPython.display import HTML, display

debug = False


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

    def __call__(self, version="0", reset=False, var_name="", var_value="", show_all=False, set_debug=None):

        if set_debug is not None:
            global debug
            debug = set_debug

        user_ns = self.shell.user_ns
        base_dir = self.shell.starting_dir + "/.cache/"

        if show_all:
            self._show_all(base_dir)
            return

        var_folder_path = os.path.join(base_dir, var_name)
        var_data_path = os.path.join(var_folder_path, "data.pkl.gz")
        var_info_path = os.path.join(var_folder_path, "info.pkl")

        if reset:
            if var_name:
                print("Resetting cached values for " + var_name)
                self._reset_var(var_folder_path)
                # no return, because it might be a forced recalculation
            else:
                print("Resetting entire cache")
                self._reset_all(base_dir)
                return

        if not var_name:
            print("Warning: nothing todo: no variable defined, no reset requested, no show_all requested. ")
            return

        version = self._get_cache_version(version, var_value, user_ns)
        stored_value = None

        try:
            info = self.get_info_from_file(var_info_path)
            self._handle_cache_hit(info, var_value, var_folder_path, version)

            try:
                stored_value = self.get_data_from_file(var_data_path)

                print('Loading cached value for variable \'{0}\'. Time since caching: {1}'
                      .format(str(var_name), str(datetime.datetime.now() - info["store_date"])))
                user_ns[var_name] = stored_value
            except IOError:
                pass  # this happens, when there was a cache hit, but it was dirty
        except IOError:
            if not var_value and not reset:
                raise CacheCallException("Variable '" + str(var_name) + "' not in cache")

        if var_value and stored_value is None:
            print('Creating new value for variable \'' + str(var_name) + '\'')
            self._create_new_value(
                self.shell,
                var_folder_path,
                var_data_path,
                var_info_path,
                version,
                var_name,
                var_value)

    @staticmethod
    def strip_line(line):
        return str(line).strip()
        # return hashlib.sha1(line.encode('utf-8')).hexdigest()

    @staticmethod
    def reset_folder(path, make_new=True):
        if os.path.exists(path):
            shutil.rmtree(path)
        if make_new:
            os.makedirs(path)

    @staticmethod
    def get_data_from_file(path):
        with open(path, 'rb') as fp:
            return pickle.loads(zlib.decompress(fp.read()))

    @staticmethod
    def get_info_from_file(path):
        with open(path, 'rb') as fp:
            return pickle.loads(fp.read())

    def _create_new_value(self, shell, var_folder_path, var_data_path, var_info_path, version, var_name, var_value):

        # make sure there is a clean state for this var
        self.reset_folder(var_folder_path)

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

    @staticmethod
    def _show_all(base_dir):
        if not os.path.isdir(base_dir):
            raise CacheCallException("Base-Directory " + base_dir + " not found. ")

        vars = []
        sizes = []
        for subdir in os.listdir(base_dir):
            var_name = subdir
            if debug:
                print("found subdir: " + var_name)

            data_path = os.path.join(base_dir, var_name, "data.pkl.gz")
            size = int(os.path.getsize(data_path)) / 1000000
            sizes.append(size)
            var_info_path = os.path.join(base_dir, subdir, "info.pkl")

            try:
                info = CacheCall.get_info_from_file(var_info_path)
                store_date = info["store_date"]
                version = info["version"]
                expression = info["expression_hash"]
                vars.append([var_name, size, store_date, version, expression])

            except IOError:
                print("Warning: failed to read info variable '" + var_name + "'")
        total_size = sum(sizes)
        vars.append(['Total Size:', total_size])
        display(HTML(tabulate(vars, headers=["Var Name", "Size(MB)", "Stored Date", "Version", "Expression"],
                              tablefmt="html")))

    @staticmethod
    def _reset_all(base_dir):
        CacheCall.reset_folder(base_dir)

    @staticmethod
    def _reset_var(var_folder_path):
        CacheCall.reset_folder(var_folder_path, False)

    @staticmethod
    def _handle_cache_hit(info, var_value, var_folder_path, version):
        """
        If there was a cache hit, this handles the invalidation of the cache, if needed
        """
        if var_value:
            # if there is an expression and no info-file -> a new variable and nothing needs to be checked up front
            if str(info["version"]) != str(version):
                # Note: Version can be a string, a number or the content of a variable (which can by anything)
                if debug:
                    print("Resetting because version mismatch")
                CacheCall.reset_folder(var_folder_path)
            elif info["expression_hash"] != CacheCall.strip_line(var_value):
                print("Warning! Expression has changed since last save, which was at " + str(info["store_date"]))
                print("To store a new value, change the version ('-v' or '--version')  ")
        else:
            if version != '' and info['version'] != version:
                # force a version
                raise CacheCallException(
                    "Forced version '" + str(version)
                    + "' could not be found, instead found version '"
                    + str(info['version']) + "'."
                    + "If you don't care about a specific version, leave out the version parameter. ")

    @staticmethod
    def _get_cache_version(version_param, var_value, user_ns):

        if version_param in user_ns.keys():
            return user_ns[version_param]
        if version_param.isdigit():
            return int(version_param)

        print("Version: " + str(version_param))
        print("version_param.isdigit(): " + str(version_param.isdigit()))
        raise CacheCallException("Invalid version. It must either be an Integer, *, or the name of a variable")

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
            print("Error: " + str(e))

    @staticmethod
    def parse_input(_input):
        result = {}
        global debug

        params = _input.strip().split(" ")
        reading_version = False
        expression_starts_at = 0
        for p in params:
            expression_starts_at = expression_starts_at + 1
            if p == "-v" or p == "--version":
                reading_version = True
                continue
            if reading_version:
                reading_version = False
                result["version"] = p
                continue
            if p == "-r" or p == "--reset":
                result["reset"] = True
                continue
            if p == "-d" or p == "--debug":
                debug = True
                continue
            if p.startswith("-"):
                raise CacheCallException("unknown parameter \"" + p + "\"")
            # if parameters are done the rest is part of the expression
            expression_starts_at = expression_starts_at - 1
            break

        # Everything after the version is the assignment getting cached
        cmd_str = "".join(params[expression_starts_at:])

        if not "version" in result and not "reset" in result and not cmd_str:
            # no input (expect debug) --> restore all
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
except:
    print("Error! Couldn't register cache magic in jupyter.")
