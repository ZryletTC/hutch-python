import logging
import importlib

logger = logging.getLogger(__name__)


def extract_objs(module_name):
    """
    Import module and return all the objects without a _ prefix. If an __all__
    keyword exists, follow that keyword's instructions instead.

    If this is a single object in a module rather than a module, import just
    that object.

    If this is a callable and it ends in (), call it and import the return
    value. Note that this includes classes.

    Parameters
    ----------
    module_name: str
        Filename, module name, or path to object in module

    Returns
    -------
    objs: dict
        Mapping from name in file to object
    """
    objs = {}
    # Allow filenames
    module_name = module_name.strip('.py')
    if '()' in module_name:
        module_name = module_name.strip('()')
        call_me = True
    else:
        call_me = False
    try:
        try:
            module = importlib.import_module(module_name)
        except ImportError:
            my_obj = find_object(module_name)
            name = module_name.split('.')[-1]
            # call_me, maybe
            if call_me:
                objs[name] = my_obj()
            else:
                objs[name] = my_obj
            return objs
    except Exception:
        logger.exception('Error loading %s', module_name)
        return objs
    all_kwd = getattr(module, '__all__', None)
    if all_kwd is None:
        all_kwd = [a for a in dir(module) if a[0] != '_']
    for attr in all_kwd:
        obj = getattr(module, attr)
        objs[attr] = obj
    return objs


def find_object(obj_path):
    """
    Given a string module path to an object, return that object.

    Parameters
    ----------
    obj_path: str
        String module path to an object

    Returns
    -------
    obj: Object
        That object
    """
    parts = obj_path.split('.')
    module_path = '.'.join(parts[:-1])
    class_name = parts[-1]
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def find_class(class_path):
    """
    Given a string class name, either return the matching built-in type or
    import the correct module and return the type.

    Parameters
    ----------
    class_path: str
        Built-in type name or import path e.g. ophyd.device.Device

    Returns
    -------
    cls: type
    """
    if '.' in class_path:
        return find_object(class_path)
    else:
        return eval(class_path)